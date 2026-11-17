"""Repositorio CRUD genérico dirigido por metadatos (consultas dinámicas y seguras).

Los identificadores (tablas/columnas) vienen SIEMPRE del catálogo y se componen con
``psycopg.sql.Identifier``; los valores viajan siempre como parámetros.
"""
from __future__ import annotations

from psycopg import sql

from Seguridad.contratos import EjecutorSQL

from ..models.meta import Entidad


_BORRADO_LOGICO = sql.SQL("UPDATE {} SET state = FALSE WHERE {} = %s")
_BORRADO_FISICO = sql.SQL("DELETE FROM {} WHERE {} = %s")


class RepositorioCrud:
    def __init__(self, db: EjecutorSQL, entidad: Entidad):
        self._db, self._e = db, entidad

    def listar(self, filtros: dict[str, object]) -> list[dict]:
        e = self._e
        condiciones = [sql.SQL("{} = %s").format(sql.Identifier(col)) for col in filtros]
        donde = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(condiciones) if condiciones else sql.SQL("")
        return self._db.fetch_all(sql.SQL("SELECT * FROM {}{} ORDER BY {}, {}").format(
            sql.Identifier(e.tabla), donde, sql.Identifier(e.orden), sql.Identifier(e.pk)), list(filtros.values()))

    def obtener(self, pk: int) -> dict | None:
        e = self._e
        return self._db.fetch_one(sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
            sql.Identifier(e.tabla), sql.Identifier(e.pk)), (pk,))

    def crear(self, datos: dict) -> dict:
        e = self._e
        columnas = list(datos)
        return self._db.fetch_one(sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
            sql.Identifier(e.tabla), sql.SQL(", ").join(map(sql.Identifier, columnas)),
            sql.SQL(", ").join(sql.Placeholder() * len(columnas))), list(datos.values()))

    def actualizar(self, pk: int, datos: dict) -> dict | None:
        e = self._e
        if not datos:
            return self.obtener(pk)
        asignaciones = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in datos)
        return self._db.fetch_one(sql.SQL("UPDATE {} SET {} WHERE {} = %s RETURNING *").format(
            sql.Identifier(e.tabla), asignaciones, sql.Identifier(e.pk)), [*datos.values(), pk])

    def eliminar(self, pk: int) -> bool:
        """Borrado lógico (state = false) si la tabla lo admite; si no, físico."""
        e = self._e
        consulta = _BORRADO_LOGICO if e.borrado_logico else _BORRADO_FISICO
        return self._db.execute(consulta.format(sql.Identifier(e.tabla), sql.Identifier(e.pk)), (pk,)) > 0
