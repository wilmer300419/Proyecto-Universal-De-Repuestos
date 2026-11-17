"""Conecta el paquete con Flask: resolución del usuario por petición, CSRF y rutas /api/auth.

La vista web (SPA) inicia sesión con POST /api/auth/sesion: el JWT viaja en una cookie HttpOnly/SameSite=Strict
y cada escritura debe enviar la cabecera X-CSRF-Token. Otros clientes pueden usar POST /api/auth/token y la
cabecera Authorization: Bearer (sin cookie, por lo que no aplica CSRF)."""
from __future__ import annotations

import hashlib
import hmac

from flask import Blueprint, Flask, current_app, g, jsonify, request

from .captcha import ServicioCaptcha
from .configuracion import ConfigSeguridad
from .contrasenas import HasherContrasena, PoliticaContrasena
from .contratos import EjecutorSQL
from .limitador import LimitadorPeticiones, Regla
from .repositorio import RepositorioAuditoria, RepositorioUsuarios
from .servicio import ErrorAutenticacion, ServicioAutenticacion
from .tokens import ServicioJWT, TokenInvalido

_METODOS_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}
api_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def servicio() -> ServicioAutenticacion:
    return current_app.extensions["seguridad"]


def _cfg() -> ConfigSeguridad:
    return current_app.extensions["seguridad_cfg"]


def _ip() -> str | None:
    return request.remote_addr


def _agente() -> str:
    return request.headers.get("User-Agent", "")


def csrf_esperado(jti: str) -> str:
    return hmac.new(_cfg().jwt_secreto.encode(), f"csrf:{jti}".encode(), hashlib.sha256).hexdigest()


def _perfil() -> dict:
    u = g.usuario
    return {"user_id": u.id, "username": u.nombre_usuario, "email": u.email, "role": u.rol.value, "rbac": u.grupo.value,
            "expira": g.claims.exp.isoformat(), "csrf_token": csrf_esperado(g.claims.jti) if g.via_cookie else None}


def inicializar_seguridad(app: Flask, db: EjecutorSQL, cfg: ConfigSeguridad) -> None:
    usuarios, auditoria = RepositorioUsuarios(db), RepositorioAuditoria(db)
    app.extensions["seguridad"] = ServicioAutenticacion(
        usuarios, auditoria, ServicioJWT(cfg), ServicioCaptcha(cfg.jwt_secreto, cfg.captcha_ttl_s),
        HasherContrasena(), PoliticaContrasena(), cfg)
    app.extensions["seguridad_cfg"] = cfg
    app.extensions["limitador"] = LimitadorPeticiones()
    app.extensions["limitador_reglas"] = {
        "/api/auth/sesion": ("login", Regla(cfg.login_por_minuto, 60)),
        "/api/auth/token": ("login", Regla(cfg.login_por_minuto, 60)),
        "/api/auth/login": ("login", Regla(cfg.login_por_minuto, 60)),
        "/api/auth/captcha": ("captcha", Regla(cfg.captcha_por_minuto, 60)),
        "/api/clientes": ("registro", Regla(cfg.registro_por_hora, 3600))}
    app.before_request(limitar_peticiones)
    app.before_request(resolver_usuario)
    app.register_blueprint(api_bp)


def limitar_peticiones():
    """OWASP A07/A04: limita intentos por IP en los endpoints de autenticación y registro (HTTP 429)."""
    regla = current_app.extensions["limitador_reglas"].get(request.path)
    if regla is None or (request.method == "GET") != (regla[0] == "captcha"):
        return None
    permitido, espera = current_app.extensions["limitador"].permitir(f"{regla[0]}:{_ip()}", regla[1])
    if permitido:
        return None
    servicio().auditoria.registrar(None, None, "LIMITE_EXCEDIDO", regla[0], request.path, _ip())
    resp = jsonify(error=f"Demasiados intentos. Espera {espera} s e intenta de nuevo.")
    resp.status_code, resp.headers["Retry-After"] = 429, str(espera)
    return resp


def _token_de_la_peticion(cfg: ConfigSeguridad) -> tuple[str | None, bool]:
    """(token, viene_de_cookie). La cabecera Authorization tiene prioridad sobre la cookie."""
    cabecera = request.headers.get("Authorization", "")
    if cabecera.lower().startswith("bearer "):
        return cabecera[7:].strip(), False
    return request.cookies.get(cfg.cookie_nombre), True


def resolver_usuario():
    g.usuario, g.claims, g.via_cookie = None, None, False
    token, via_cookie = _token_de_la_peticion(_cfg())
    if not token:
        return None
    try:
        g.usuario, g.claims = servicio().autenticar_token(token, _agente())
    except TokenInvalido:
        return None
    g.via_cookie = via_cookie
    if via_cookie and request.method in _METODOS_ESCRITURA:          # protección CSRF
        enviado = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(enviado, csrf_esperado(g.claims.jti)):
            return jsonify(error="La sesión del formulario venció. Recarga la página e intenta de nuevo."), 400
    return None


# ------------------------------------------------------------------ API
@api_bp.get("/captcha")
def captcha_nuevo():
    svg, token = servicio().captcha.generar()
    resp = jsonify(svg=svg, token=token)
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _login(datos: dict):
    return servicio().iniciar_sesion(datos.get("usuario", ""), datos.get("password", ""), datos.get("captcha_token", ""),
                                     datos.get("captcha", ""), _ip(), _agente())


@api_bp.post("/sesion")
def api_sesion():
    """Inicio de sesión de la vista web: deja el JWT en una cookie HttpOnly y devuelve el token CSRF."""
    try:
        token, claims, u = _login(request.get_json(silent=True) or {})
    except ErrorAutenticacion as e:
        return jsonify(error=str(e)), 401
    cfg = _cfg()
    resp = jsonify(user_id=u.id, username=u.nombre_usuario, email=u.email, role=u.rol.value,
                   expira=claims.exp.isoformat(), csrf_token=csrf_esperado(claims.jti))
    resp.set_cookie(cfg.cookie_nombre, token, max_age=cfg.jwt_expira_min * 60, httponly=True,
                    secure=cfg.cookie_segura, samesite="Strict", path="/")
    return resp


@api_bp.post("/token")
@api_bp.post("/login")
def api_token():
    """Inicio de sesión para clientes de API (Authorization: Bearer).
    /api/auth/login es el endpoint de la Guía 7 (POST /login): misma función, sin duplicar lógica."""
    try:
        token, claims, u = _login(request.get_json(silent=True) or {})
    except ErrorAutenticacion as e:
        return jsonify(error=str(e)), 401
    return jsonify(access_token=token, token_type="Bearer", expires_in=_cfg().jwt_expira_min * 60, role=u.rol.value,  # noqa: S106
                   rbac=u.grupo.value)


@api_bp.get("/yo")
def api_yo():
    """Perfil de la sesión actual. Con ?opcional=1 responde 200 {autenticado: false} en lugar de 401
    (la SPA lo usa al cargar, cuando el visitante puede no haber iniciado sesión)."""
    if not g.usuario:
        if request.args.get("opcional"):
            return jsonify(autenticado=False)
        return jsonify(error="No autenticado"), 401
    return jsonify(autenticado=True, **_perfil())


def _sin_cookie(resp):
    resp.delete_cookie(_cfg().cookie_nombre, path="/")
    return resp


@api_bp.post("/logout")
def api_logout():
    if not g.claims:
        return _sin_cookie(jsonify(mensaje="No había una sesión activa"))
    try:
        servicio().cerrar_sesion(g.claims, _ip())
    except TokenInvalido:
        return _sin_cookie(jsonify(error="La sesión ya no está activa")), 409
    return _sin_cookie(jsonify(mensaje="Sesión cerrada y token revocado"))


@api_bp.post("/logout-todas")
def api_logout_todas():
    if not g.usuario:
        return jsonify(error="No autenticado"), 401
    n = servicio().cerrar_todas(g.usuario.id, g.usuario.nombre_usuario, ip=_ip())
    return _sin_cookie(jsonify(mensaje="Sesiones cerradas", sesiones=n))


@api_bp.get("/sesiones")
def api_sesiones():
    if not g.usuario:
        return jsonify(error="No autenticado"), 401
    filas = servicio().usuarios.sesiones_activas(g.usuario.id)
    return jsonify([{"sesion": f["jti"][:8], "actual": f["jti"] == g.claims.jti, "emitida": f["emitido_en"].isoformat(),
                     "expira": f["expira_en"].isoformat(), "ip": f["ip"]} for f in filas])
