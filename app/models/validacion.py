"""MODELO (MVC): conversión y validación de entradas, compartida por todos los servicios.

Funciones puras: no conocen Flask ni la base de datos. Lanzan ``ErrorValidacion`` (HTTP 400)
con un mensaje seguro para el usuario; nunca dejan escapar ``ValueError``/``TypeError`` (HTTP 500).
"""
from __future__ import annotations

from .errores import ErrorValidacion

_VERDADEROS = frozenset({"1", "true", "t", "si", "sí", "yes", "on"})
_FALSOS = frozenset({"0", "false", "f", "no", "off"})


def a_booleano(valor, nombre: str = "valor") -> bool:
    """Convierte de forma ESTRICTA: 'false', '0' o 'no' son False (bool('false') sería True)."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int) and valor in (0, 1):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in _VERDADEROS:
        return True
    if texto in _FALSOS:
        return False
    raise ErrorValidacion(f"{nombre} debe ser verdadero o falso")


def a_entero(valor, nombre: str = "valor", minimo: int | None = None, maximo: int | None = None) -> int:
    """Entero estricto: rechaza booleanos, decimales y texto."""
    if isinstance(valor, bool):
        raise ErrorValidacion(f"{nombre} debe ser un número entero")
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErrorValidacion(f"{nombre} debe ser un número entero") from None
    if minimo is not None and n < minimo:
        raise ErrorValidacion(f"{nombre} no puede ser menor que {minimo}")
    if maximo is not None and n > maximo:
        raise ErrorValidacion(f"{nombre} no puede ser mayor que {maximo}")
    return n


def entero_opcional(valor, nombre: str = "valor", minimo: int | None = 1) -> int | None:
    return None if valor in (None, "") else a_entero(valor, nombre, minimo)


def texto(valor, nombre: str, maximo: int, requerido: bool = False) -> str | None:
    limpio = str(valor if valor is not None else "").strip()
    if not limpio:
        if requerido:
            raise ErrorValidacion(f"{nombre} es obligatorio")
        return None
    if len(limpio) > maximo:
        raise ErrorValidacion(f"{nombre} admite máximo {maximo} caracteres")
    return limpio


def patron_like(busqueda: str) -> str:
    """Patrón seguro para ILIKE: escapa los comodines % y _ que escriba el usuario."""
    escapado = busqueda.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"
