"""MODELO (MVC): estructura neutral de un informe.

Los reportes producen un ``Informe``; la vista HTML (SPA, vía JSON) y la vista PDF
(ReportLab) lo consumen sin conocer el origen de los datos.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tabla:
    titulo: str
    columnas: list[str]
    filas: list[list]
    total: int | None = None        # total real si ``filas`` fue recortada
    nota: str = ""


@dataclass
class Serie:
    nombre: str
    valores: list[float]


@dataclass
class Grafico:
    titulo: str
    tipo: str                       # pie | bar | barh
    etiquetas: list[str]
    series: list[Serie]
    descripcion: str = ""


@dataclass
class Informe:
    titulo: str
    subtitulo: str = ""
    parametros: list[tuple[str, str]] = field(default_factory=list)
    bloques: list[Tabla | Grafico] = field(default_factory=list)
    horizontal: bool = False        # PDF apaisado cuando hay tablas anchas


@dataclass(frozen=True)
class Parametro:
    nombre: str
    etiqueta: str
    tipo: str = "texto"             # texto | entero | select | fecha
    por_defecto: object = ""
    opciones: tuple[tuple[str, str], ...] = ()
    minimo: int | None = None
    maximo: int | None = None
    requerido: bool = True
    ayuda: str = ""
