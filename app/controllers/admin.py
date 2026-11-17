"""Usuarios (registro de clientes y personal), auditoría, indicadores y reportes."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, request

from Seguridad import Rol, rol_requerido

from ..models.errores import ErrorValidacion
from ..reportes.pdf import generar_pdf
from ._comun import datos, ip, servicio, usuario

bp = Blueprint("admin", __name__, url_prefix="/api")
ADMIN = Rol.ADMINISTRADOR


# ------------------------------------------------------------------ usuarios
@bp.post("/clientes")
def registrar_cliente():
    """Registro público de clientes."""
    return jsonify(servicio("usuarios").registrar_cliente(datos(), ip())), 201


@bp.get("/usuarios")
@rol_requerido(ADMIN)
def listar_usuarios():
    return jsonify(servicio("usuarios").listar(request.args.get("role")))


@bp.post("/usuarios")
@rol_requerido(ADMIN)
def crear_personal():
    return jsonify(servicio("usuarios").crear_personal(datos(), usuario(), ip())), 201


@bp.put("/usuarios/<int:user_id>")
@rol_requerido(ADMIN)
def actualizar_usuario(user_id):
    return jsonify(servicio("usuarios").actualizar(user_id, datos(), usuario(), ip()))


@bp.post("/usuarios/<int:user_id>/cerrar-sesiones")
@rol_requerido(ADMIN)
def cerrar_sesiones(user_id):
    return jsonify(sesiones=servicio("usuarios").cerrar_sesiones(user_id, usuario(), ip()))


@bp.get("/auditoria")
@rol_requerido(ADMIN)
def auditoria():
    repo = servicio("auditoria")
    pagina = max(1, request.args.get("pagina", 1, type=int))
    tamano = min(100, max(5, request.args.get("tamano", 25, type=int)))
    filas, total = repo.listar(request.args.get("accion", ""), request.args.get("usuario", "").strip(), tamano, (pagina - 1) * tamano)
    return jsonify(filas=filas, total=total, pagina=pagina, tamano=tamano, acciones=repo.acciones())


# ------------------------------------------------------------------ indicadores y reportes
@bp.get("/reports/summary")
@rol_requerido(ADMIN)
def resumen():
    repo = servicio("repo_reportes")
    return jsonify({**repo.indicadores(), "by_state": repo.por_estado(), "monthly": repo.por_mes(),
                    "top_products": repo.mas_vendidos()})


def _reporte(slug):
    return servicio("reportes").get(slug) or abort(404)


def _ejecutar(slug):
    r = _reporte(slug)
    valores, errores = r.validar(request.args)
    if errores:
        raise ErrorValidacion(" ".join(errores.values()), errores)
    servicio("auditoria").registrar(usuario().id, usuario().nombre_usuario, "REPORTE", f"reporte:{slug}",
                                    request.query_string.decode()[:300], ip())
    return r, r.generar(valores)


@bp.get("/reportes")
@rol_requerido(ADMIN)
def reportes():
    return jsonify([r.describir() for r in servicio("reportes").values()])


@bp.get("/reportes/<slug>")
@rol_requerido(ADMIN)
def ver_reporte(slug):
    from dataclasses import asdict
    _, informe = _ejecutar(slug)
    bloques = [{**asdict(b), "clase": "tabla" if hasattr(b, "columnas") else "grafico"} for b in informe.bloques]
    return jsonify(titulo=informe.titulo, subtitulo=informe.subtitulo, parametros=informe.parametros, bloques=bloques)


@bp.get("/reportes/<slug>/pdf")
@rol_requerido(ADMIN)
def reporte_pdf(slug):
    r, informe = _ejecutar(slug)
    disposicion = "attachment" if request.args.get("descargar") else "inline"
    return Response(generar_pdf(informe, usuario().nombre_usuario), mimetype="application/pdf", headers={
        "Content-Disposition": f'{disposicion}; filename="repuestos-{r.slug}.pdf"', "Cache-Control": "no-store"})
