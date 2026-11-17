"""Rutas genéricas de los catálogos declarados en app/models/catalogo.py:
GET/POST /api/<slug>, GET/PUT/DELETE /api/<slug>/<id>. Lectura pública (salvo ``lectura_admin``), escritura del administrador."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from Seguridad import Rol, rol_requerido

from ..models.catalogo import ENTIDADES
from ._comun import datos, ip, servicio, usuario

bp = Blueprint("catalogo", __name__, url_prefix="/api")


def _registrar(e):
    leer = rol_requerido(Rol.ADMINISTRADOR) if e.lectura_admin else (lambda f: f)
    escribir = rol_requerido(Rol.ADMINISTRADOR)

    def listar():
        return jsonify(servicio("crud").listar(e, request.args))

    def obtener(id):
        return jsonify(servicio("crud").obtener(e, id))

    def crear():
        return jsonify(servicio("crud").crear(e, datos(), usuario(), ip())), 201

    def actualizar(id):
        return jsonify(servicio("crud").actualizar(e, id, datos(), usuario(), ip()))

    def eliminar(id):
        servicio("crud").eliminar(e, id, usuario(), ip())
        return "", 204

    bp.add_url_rule(f"/{e.slug}", f"{e.slug}_listar", leer(listar), methods=["GET"])
    bp.add_url_rule(f"/{e.slug}/<int:id>", f"{e.slug}_obtener", leer(obtener), methods=["GET"])
    bp.add_url_rule(f"/{e.slug}", f"{e.slug}_crear", escribir(crear), methods=["POST"])
    bp.add_url_rule(f"/{e.slug}/<int:id>", f"{e.slug}_actualizar", escribir(actualizar), methods=["PUT"])
    bp.add_url_rule(f"/{e.slug}/<int:id>", f"{e.slug}_eliminar", escribir(eliminar), methods=["DELETE"])


for _e in ENTIDADES:
    _registrar(_e)
