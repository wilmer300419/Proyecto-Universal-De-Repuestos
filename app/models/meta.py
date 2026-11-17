"""MODELO (MVC): descripción declarativa de los catálogos administrables.

Cada ``Entidad`` describe una tabla y sus campos; el repositorio y el servicio CRUD genéricos
trabajan solo con estos metadatos. Agregar un catálogo = declarar otra ``Entidad`` (abierto/cerrado).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str = "texto"            # texto | entero | booleano | fk
    requerido: bool = True
    max_len: int | None = None
    minimo: int | None = None
    por_defecto: object = None


@dataclass(frozen=True)
class Entidad:
    slug: str                      # segmento de la URL: /api/<slug>
    singular: str
    tabla: str
    pk: str
    campos: tuple[Campo, ...]
    orden: str = "name"
    lectura_admin: bool = False    # True: solo el administrador puede leerla
    ids_protegidos: tuple[int, ...] = ()   # registros que usa el código y no se pueden modificar

    @property
    def columnas(self) -> list[str]:
        return [self.pk] + [c.nombre for c in self.campos]

    def campo(self, nombre: str) -> Campo | None:
        return next((c for c in self.campos if c.nombre == nombre), None)

    @property
    def borrado_logico(self) -> bool:
        return self.campo("state") is not None
