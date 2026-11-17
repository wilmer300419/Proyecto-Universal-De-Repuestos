"""Generación de códigos únicos (guías de envío y referencias de pago)."""
from __future__ import annotations

import secrets


def numero_guia() -> str:
    return f"GUIA-{secrets.token_hex(5).upper()}"


def referencia_pago() -> str:
    return secrets.token_hex(6).upper()
