"""Errores de la aplicación. No conocen HTTP: el controlador decide el código con ``codigo``."""
from __future__ import annotations


class ErrorAplicacion(Exception):
    codigo = 400

    def __init__(self, mensaje: str, campos: dict[str, str] | None = None):
        super().__init__(mensaje)
        self.mensaje, self.campos = mensaje, campos or {}


class ErrorValidacion(ErrorAplicacion):
    codigo = 400


class SinPermiso(ErrorAplicacion):
    codigo = 403


class NoEncontrado(ErrorAplicacion):
    codigo = 404


class ErrorDeNegocio(ErrorAplicacion):
    """Regla de negocio incumplida (estado inválido, stock insuficiente…). Mensaje seguro para el usuario."""
    codigo = 409
