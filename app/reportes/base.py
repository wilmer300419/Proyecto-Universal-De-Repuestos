"""Infraestructura de reportes (abierto/cerrado): un reporte nuevo = una clase nueva registrada en registro.py."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from collections.abc import Mapping

from ..models.informe import Informe, Parametro, Tabla
from ..repositories.reportes import RepositorioReportes
from ..utils.fechas import formatear_fecha, parsear_fecha


def _entero(prm: Parametro, texto: str) -> int:
    try:
        n = int(texto)
    except ValueError:
        raise ValueError("ingrese un número entero.") from None
    if prm.minimo is not None and n < prm.minimo:
        raise ValueError(f"el mínimo es {prm.minimo}.")
    if prm.maximo is not None and n > prm.maximo:
        raise ValueError(f"el máximo es {prm.maximo}.")
    return n


def _opcion(prm: Parametro, texto: str) -> str:
    if texto not in {v for v, _ in prm.opciones}:
        raise ValueError("opción no válida.")
    return texto


def _fecha(_prm: Parametro, texto: str):
    if (d := parsear_fecha(texto)) is None:
        raise ValueError("use el formato AAAA-MM-DD.")
    return d


_CONVERTIDORES = {"entero": _entero, "select": _opcion, "fecha": _fecha}


class Reporte(ABC):
    slug: str
    titulo: str
    descripcion: str

    def __init__(self, repo: RepositorioReportes, filas_max: int = 5000):
        self._repo, self._filas_max = repo, filas_max

    @abstractmethod
    def parametros(self) -> list[Parametro]: ...

    @abstractmethod
    def generar(self, p: dict) -> Informe: ...

    # ----------------------------------------------------------------- común
    def describir(self) -> dict:
        return {"slug": self.slug, "titulo": self.titulo, "descripcion": self.descripcion,
                "parametros": [asdict(p) for p in self.parametros()]}

    def validar(self, crudo: Mapping[str, str]) -> tuple[dict, dict[str, str]]:
        valores, errores = {}, {}
        for prm in self.parametros():
            texto = str(crudo.get(prm.nombre, prm.por_defecto) or "").strip()
            try:
                valores[prm.nombre] = self._convertir(prm, texto)
            except ValueError as exc:
                errores[prm.nombre] = f"{prm.etiqueta}: {exc}"
        if not errores:
            errores.update(self.validar_conjunto(valores))
        return valores, errores

    def validar_conjunto(self, valores: dict) -> dict[str, str]:
        return {}

    @staticmethod
    def _convertir(prm: Parametro, texto: str):
        if not texto:
            if prm.requerido:
                raise ValueError("este campo es obligatorio.")
            return None
        convertidor = _CONVERTIDORES.get(prm.tipo)
        return convertidor(prm, texto) if convertidor else texto[:100]

    def etiquetas_parametros(self, valores: dict) -> list[tuple[str, str]]:
        salida = []
        for prm in self.parametros():
            v = valores.get(prm.nombre)
            if prm.tipo == "select":
                v = dict(prm.opciones).get(v, v)
            elif prm.tipo == "fecha" and v:
                v = formatear_fecha(v)
            salida.append((prm.etiqueta, "—" if v in (None, "") else str(v)))
        return salida

    def tabla(self, titulo: str, columnas: list[str], filas: list[list]) -> Tabla:
        total = len(filas)
        t = Tabla(titulo, columnas, filas[: self._filas_max], total=total)
        if total > self._filas_max:
            t.nota = f"Se muestran {self._filas_max} de {total} filas."
        return t
