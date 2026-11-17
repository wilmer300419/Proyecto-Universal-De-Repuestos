from __future__ import annotations

from flask import current_app, g, request

from Seguridad import Usuario


def servicio(nombre: str):
    return current_app.extensions[nombre]


def datos() -> dict:
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def ip() -> str | None:
    return request.remote_addr


def usuario() -> Usuario:
    return g.usuario
