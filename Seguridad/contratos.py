"""Contratos (Principio de Inversión de Dependencias): Seguridad depende de esta
interfaz, no de la implementación concreta de la base de datos."""
from __future__ import annotations

from typing import Any, Protocol
from collections.abc import Sequence


class EjecutorSQL(Protocol):
    def fetch_one(self, sql: Any, params: Sequence | dict | None = None) -> dict | None: ...
    def fetch_all(self, sql: Any, params: Sequence | dict | None = None) -> list[dict]: ...
    def execute(self, sql: Any, params: Sequence | dict | None = None) -> int: ...
