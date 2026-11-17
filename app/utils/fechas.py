"""Utilería de fechas."""
from __future__ import annotations

import re
from datetime import date, datetime


def formatear_fecha(valor: date | datetime | None) -> str:
    """DD/MM/AAAA."""
    return valor.strftime("%d/%m/%Y") if valor else ""


def parsear_fecha(valor) -> date | None:
    """Acepta date, datetime, 2026-03-11 y 11/03/2026."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto):
        return _seguro(int(m[1]), int(m[2]), int(m[3]))
    if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto):
        return _seguro(int(m[3]), int(m[2]), int(m[1]))
    return None


def _seguro(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None
