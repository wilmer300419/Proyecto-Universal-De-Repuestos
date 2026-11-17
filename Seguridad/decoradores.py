from __future__ import annotations

from functools import wraps

from flask import g, jsonify, redirect, request

from .modelos import Grupo, Rol, Usuario


def usuario_actual() -> Usuario | None:
    return getattr(g, "usuario", None)


def _es_api() -> bool:
    return request.path.startswith("/api/")


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            if _es_api():
                return jsonify(error="Debes iniciar sesión"), 401
            return redirect("/#/login")
        return vista(*args, **kwargs)
    return envoltura


def rol_requerido(*roles: Rol):
    permitidos = {r.value if isinstance(r, Rol) else r for r in roles}

    def decorador(vista):
        @wraps(vista)
        @login_requerido
        def envoltura(*args, **kwargs):
            if usuario_actual().rol.value not in permitidos:
                return jsonify(error="Tu rol no permite realizar esta acción"), 403
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def grupo_requerido(*grupos: Grupo):
    """RBAC por grupo: ADMIN o USER. El permiso SIEMPRE se decide con el usuario cargado de la base de datos
    (g.usuario), no con los claims del token: un cambio de rol surte efecto de inmediato."""
    permitidos = {gr.value if isinstance(gr, Grupo) else gr for gr in grupos}

    def decorador(vista):
        @wraps(vista)
        @login_requerido
        def envoltura(*args, **kwargs):
            if usuario_actual().grupo.value not in permitidos:
                return jsonify(error="Acceso denegado: se requiere el rol " + " o ".join(sorted(permitidos))), 403
            return vista(*args, **kwargs)
        return envoltura
    return decorador
