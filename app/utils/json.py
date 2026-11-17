"""Serialización JSON de los tipos que devuelve PostgreSQL (Decimal, fechas)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


class ProveedorJSON(DefaultJSONProvider):
    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return DefaultJSONProvider.default(o)
