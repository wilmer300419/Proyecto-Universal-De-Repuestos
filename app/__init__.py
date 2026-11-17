"""Fábrica de la aplicación Flask (patrón MVC).

* Modelos:       app/models (reglas de negocio y metadatos), app/repositories (SQL), app/services (casos de uso)
* Vistas:        app/templates + app/static (SPA de tienda y panel), app/reportes/pdf.py y app/documentos (PDF)
* Controladores: app/controllers (blueprints JSON) y Seguridad/ (autenticación)
"""
from __future__ import annotations

import atexit
import logging

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from Seguridad import ConfigSeguridad, inicializar_seguridad
from Seguridad.repositorio import RepositorioAuditoria
from Seguridad.servicio import DatosUsuarioInvalidos

from .config import Configuracion
from .core.database import Database
from .documentos.factura import DocumentosFactura
from .models.errores import ErrorAplicacion
from .repositories.reportes import RepositorioReportes
from .reportes.registro import construir_reportes
from .services.crud import ServicioCrud
from .services.productos import ServicioProductos
from .services.usuarios import ServicioUsuarios
from .services.ventas import ServicioEntregas, ServicioFacturas, ServicioVentas
from .utils.json import ProveedorJSON

CSP = ("default-src 'self'; script-src 'self'; script-src-attr 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; connect-src 'self'; frame-src https://maps.google.com https://www.google.com; "
       "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")


def crear_app(config: Configuracion | None = None) -> Flask:
    load_dotenv()
    cfg = config or Configuracion.desde_entorno()
    app = Flask(__name__)
    app.json = ProveedorJSON(app)
    app.config.update(SECRET_KEY=cfg.secret_key, MAX_CONTENT_LENGTH=1 * 1024 * 1024, ENTORNO=cfg.entorno, CFG=cfg)

    db = Database(cfg.database_url)
    db.abrir()
    atexit.register(db.cerrar)
    app.extensions["db"] = db

    inicializar_seguridad(app, db, ConfigSeguridad(jwt_secreto=cfg.jwt_secret, jwt_expira_min=cfg.jwt_expira_min,
                                                   cookie_segura=cfg.cookie_segura, login_por_minuto=cfg.login_por_minuto,
                                                   registro_por_hora=cfg.registro_por_hora))
    auditoria = RepositorioAuditoria(db)
    repo_reportes = RepositorioReportes(db)
    app.extensions.update(
        auditoria=auditoria,
        crud=ServicioCrud(db, auditoria),
        productos=ServicioProductos(db, auditoria),
        ventas=ServicioVentas(db, auditoria, cfg.iva),
        entregas=ServicioEntregas(db),
        facturas=ServicioFacturas(db, DocumentosFactura(cfg.dir_facturas), cfg.iva),
        usuarios=ServicioUsuarios(db, app.extensions["seguridad"]),
        repo_reportes=repo_reportes,
        reportes=construir_reportes(repo_reportes, cfg.filas_pdf_max),
    )

    from .controllers import admin, catalogo, main, productos, ventas
    for modulo in (main, catalogo, productos, ventas, admin):
        app.register_blueprint(modulo.bp)

    _cabeceras_y_cors(app, cfg)
    _registro_de_seguridad(app)

    _manejadores_de_error(app)
    from .cli import registrar_comandos
    registrar_comandos(app)
    return app


def _cabeceras_y_cors(app: Flask, cfg: Configuracion) -> None:
    @app.before_request
    def preflight_cors():
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            return app.make_default_options_response()
        return None

    @app.after_request
    def cabeceras(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        if cfg.cookie_segura:                   # solo cuando se sirve por HTTPS
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
            origen = (request.headers.get("Origin") or "").rstrip("/")
            if origen and origen in cfg.cors_origenes:          # CORS solo para orígenes de la lista blanca
                resp.headers["Access-Control-Allow-Origin"] = origen
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRF-Token"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                resp.headers["Access-Control-Max-Age"] = "600"
            resp.headers.add("Vary", "Origin")
        return resp


def _registro_de_seguridad(app: Flask) -> None:
    """OWASP A09: deja en el log de la aplicación los rechazos de acceso y errores, sin datos sensibles
    (ni contraseñas, ni tokens, ni cuerpos de petición). Los eventos de negocio van a la tabla auditoria."""
    registro = logging.getLogger("repuestos.seguridad")
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.after_request
    def registrar(resp):
        if resp.status_code in (401, 403, 429) or resp.status_code >= 500:
            u = getattr(g, "usuario", None)
            registro.warning("acceso_rechazado status=%s metodo=%s ruta=%s ip=%s usuario=%s", resp.status_code,
                             request.method, request.path, request.remote_addr, u.id if u else "-")
        return resp


def _manejadores_de_error(app: Flask) -> None:
    @app.errorhandler(ErrorAplicacion)
    def error_aplicacion(e: ErrorAplicacion):
        return jsonify(error=e.mensaje, campos=e.campos or None), e.codigo

    @app.errorhandler(DatosUsuarioInvalidos)
    def datos_invalidos(e: DatosUsuarioInvalidos):
        return jsonify(error=e.mensaje()), 400

    @app.errorhandler(HTTPException)
    def http(e: HTTPException):
        if not request.path.startswith("/api/") and e.code == 404:
            return render_template("index.html"), 404
        mensajes = {404: "Recurso no encontrado", 405: "Método no permitido", 413: "La solicitud es demasiado grande"}
        return jsonify(error=mensajes.get(e.code, e.description)), e.code

    @app.errorhandler(Exception)
    def inesperado(e: Exception):
        app.logger.exception(e)
        return jsonify(error="Ocurrió un problema inesperado. Intenta de nuevo."), 500
