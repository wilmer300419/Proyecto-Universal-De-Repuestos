"""Formatos de presentación (usados por plantillas y PDF)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from .fechas import formatear_fecha


def moneda(valor) -> str:
    """4395489 -> '$ 4.395.489' (pesos colombianos)."""
    if valor is None or valor == "":
        return ""
    return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")


def celda(valor) -> str:
    """Convierte cualquier valor de BD a texto legible."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return formatear_fecha(valor)
    if isinstance(valor, Decimal):
        return f"{valor:f}".rstrip("0").rstrip(".") if "." in f"{valor:f}" else f"{valor}"
    return str(valor)
