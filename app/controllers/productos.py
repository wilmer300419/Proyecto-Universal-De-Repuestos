from __future__ import annotations

from flask import Blueprint, jsonify, request

from Seguridad import Rol, rol_requerido

from ._comun import datos, ip, servicio, usuario

bp = Blueprint("productos", __name__, url_prefix="/api")
ADMIN = Rol.ADMINISTRADOR


@bp.get("/products")
def listar():
    a = request.args
    return jsonify(servicio("productos").buscar(a.get("q"), a.get("car_id"), a.get("car_brand_id"), a.get("type_id"),
                                                a.get("warehouse_id")))


@bp.get("/products/<int:product_id>")
def obtener(product_id):
    return jsonify(servicio("productos").obtener(product_id, request.args.get("warehouse_id")))


@bp.get("/cars/<int:car_id>/products")
def para_vehiculo(car_id):
    return jsonify(servicio("productos").para_vehiculo(car_id))


@bp.post("/products")
@rol_requerido(ADMIN)
def crear():
    return jsonify(servicio("productos").crear(datos(), usuario(), ip())), 201


@bp.put("/products/<int:product_id>")
@rol_requerido(ADMIN)
def actualizar(product_id):
    return jsonify(servicio("productos").actualizar(product_id, datos(), usuario(), ip()))


@bp.delete("/products/<int:product_id>")
@rol_requerido(ADMIN)
def desactivar(product_id):
    servicio("productos").desactivar(product_id, usuario(), ip())
    return "", 204


@bp.get("/inventory")
@rol_requerido(ADMIN, Rol.EMPACADOR)
def inventario():
    return jsonify(servicio("productos").listar_inventario(request.args.get("warehouse_id"), request.args.get("low") == "1"))


@bp.post("/inventory")
@rol_requerido(ADMIN)
def crear_inventario():
    return jsonify(servicio("productos").crear_inventario(datos(), usuario(), ip())), 201


@bp.put("/inventory/<int:inventory_id>")
@rol_requerido(ADMIN)
def actualizar_inventario(inventory_id):
    return jsonify(servicio("productos").actualizar_inventario(inventory_id, datos(), usuario(), ip()))
