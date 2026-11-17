from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file

from Seguridad import Rol, login_requerido, rol_requerido

from ._comun import datos, ip, servicio, usuario

bp = Blueprint("ventas", __name__, url_prefix="/api")
COMPRAN = (Rol.CLIENTE, Rol.ADMINISTRADOR)
ADMIN = Rol.ADMINISTRADOR


# ------------------------------------------------------------------ ventas y pagos
@bp.get("/sales/payment-methods")
def metodos_pago():
    return jsonify(servicio("ventas").metodos_pago())


@bp.post("/sales")
@rol_requerido(*COMPRAN)
def crear_venta():
    return jsonify(servicio("ventas").crear(datos(), usuario(), ip())), 201


@bp.get("/sales")
@login_requerido
def listar_ventas():
    return jsonify(servicio("ventas").listar(usuario(), request.args.get("state")))


@bp.get("/sales/<int:sale_id>")
@login_requerido
def obtener_venta(sale_id):
    return jsonify(servicio("ventas").obtener(sale_id, usuario()))


@bp.post("/sales/<int:sale_id>/payments")
@rol_requerido(*COMPRAN)
def pagar(sale_id):
    return jsonify(servicio("ventas").pagar(sale_id, datos(), usuario(), ip())), 201


@bp.post("/sales/<int:sale_id>/cancel")
@rol_requerido(*COMPRAN)
def cancelar(sale_id):
    return jsonify(servicio("ventas").cancelar(sale_id, usuario(), ip()))


# ------------------------------------------------------------------ entregas
@bp.get("/deliveries")
@rol_requerido(ADMIN, Rol.EMPACADOR)
def entregas():
    return jsonify(servicio("entregas").listar(request.args.get("status")))


@bp.get("/deliveries/assigned")
@rol_requerido(Rol.REPARTIDOR)
def entregas_asignadas():
    return jsonify(servicio("entregas").asignadas(usuario(), request.args.get("status")))


@bp.get("/deliveries/track/<guia>")
def rastrear(guia):
    return jsonify(servicio("entregas").rastrear(guia))


@bp.post("/deliveries/<int:delivery_id>/prepare")
@rol_requerido(Rol.EMPACADOR, ADMIN)
def preparar(delivery_id):
    return jsonify(servicio("entregas").preparar(delivery_id, usuario(), ip()))


@bp.post("/deliveries/<int:delivery_id>/assign")
@rol_requerido(ADMIN)
def asignar(delivery_id):
    return jsonify(servicio("entregas").asignar(delivery_id, datos().get("user_id"), usuario(), ip()))


@bp.patch("/deliveries/<int:delivery_id>/status")
@rol_requerido(Rol.REPARTIDOR, ADMIN)
def cambiar_estado(delivery_id):
    return jsonify(servicio("entregas").avanzar(delivery_id, datos().get("status"), usuario(), ip()))


# ------------------------------------------------------------------ facturas
@bp.post("/sales/<int:sale_id>/invoice")
@rol_requerido(ADMIN)
def emitir_factura(sale_id):
    return jsonify(servicio("facturas").emitir(sale_id, usuario(), ip())), 201


@bp.get("/sales/<int:sale_id>/invoice")
@login_requerido
def factura_de_venta(sale_id):
    return jsonify(servicio("facturas").por_venta(sale_id, usuario()))


@bp.get("/invoices/<int:invoice_id>/pdf")
@login_requerido
def factura_pdf(invoice_id):
    f = servicio("facturas").pdf(invoice_id, usuario())
    return send_file(f["pdf_path"], mimetype="application/pdf", as_attachment=True, download_name=f"{f['invoice_number']}.pdf")
