from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from Seguridad import Grupo, grupo_requerido

from ._comun import usuario

bp = Blueprint("main", __name__)


@bp.get("/")
def inicio():
    """VISTA: la SPA (tienda y panel) se sirve desde una plantilla; los datos llegan por la API JSON."""
    return render_template("index.html")


@bp.get("/api/salud")
def salud():
    return jsonify(estado="ok")


# ------------------------------------------------------------------ demostración RBAC (Guía 7)
def _identidad() -> dict:
    u = usuario()
    return {"user_id": u.id, "username": u.nombre_usuario, "role": u.rol.value, "rbac": u.grupo.value}


@bp.get("/api/admin")
@grupo_requerido(Grupo.ADMIN)
def solo_admin():
    """Acceso exclusivo para ADMIN (rol administrador)."""
    return jsonify(mensaje="Acceso concedido al área de administración", **_identidad())


@bp.get("/api/user")
@grupo_requerido(Grupo.USER, Grupo.ADMIN)
def usuario_autenticado():
    """Acceso para USER (cliente, empacador, repartidor) y también para ADMIN."""
    return jsonify(mensaje="Acceso concedido al área de usuario", **_identidad())
