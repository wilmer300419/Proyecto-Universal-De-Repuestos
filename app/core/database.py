"""Acceso a PostgreSQL mediante un pool de conexiones (psycopg 3).

Es la única clase que conoce el driver; el resto del sistema depende de sus métodos
(fetch_all / fetch_one / execute / transaccion), no del driver. Todas las conexiones usan el
esquema ``automotriz`` (search_path) y la zona horaria de Bogotá.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from collections.abc import Iterator, Sequence

from psycopg import Connection, OperationalError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from migraciones import OPCIONES_CONEXION


class EjecutorConexion:
    """Misma interfaz que ``Database`` pero sobre UNA conexión ya abierta: permite que varios
    repositorios trabajen dentro de la misma transacción."""

    def __init__(self, conn: Connection):
        self._conn = conn

    def fetch_all(self, sql: Any, params: Sequence | dict | None = None) -> list[dict]:
        return self._conn.execute(sql, params).fetchall()

    def fetch_one(self, sql: Any, params: Sequence | dict | None = None) -> dict | None:
        return self._conn.execute(sql, params).fetchone()

    def execute(self, sql: Any, params: Sequence | dict | None = None) -> int:
        return self._conn.execute(sql, params).rowcount


class Database:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10):
        # check: antes de entregar una conexión se verifica que siga viva (reinicios de PostgreSQL, cortes de red);
        # max_idle/max_lifetime reciclan conexiones viejas.
        self._pool = ConnectionPool(dsn, min_size=min_size, max_size=max_size, check=ConnectionPool.check_connection,
                                    max_idle=300, max_lifetime=3600, timeout=10,
                                    kwargs={"row_factory": dict_row, "options": OPCIONES_CONEXION}, open=False)

    def abrir(self) -> None:
        try:
            self._pool.open(wait=True, timeout=15)
        except (PoolTimeout, OperationalError) as exc:
            raise RuntimeError("No fue posible conectarse a PostgreSQL. Revisa DATABASE_URL en .env "
                               "y que el servidor esté en ejecución.") from exc

    def cerrar(self) -> None:
        self._pool.close()

    @contextmanager
    def transaccion(self) -> Iterator[Connection]:
        """Conexión con commit al salir y rollback ante cualquier excepción."""
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def unidad_de_trabajo(self) -> Iterator[EjecutorConexion]:
        """Transacción expuesta como ejecutor SQL (para pasarla a los repositorios)."""
        with self.transaccion() as conn:
            yield EjecutorConexion(conn)

    def fetch_all(self, sql: Any, params: Sequence | dict | None = None) -> list[dict]:
        with self.transaccion() as conn:
            return conn.execute(sql, params).fetchall()

    def fetch_one(self, sql: Any, params: Sequence | dict | None = None) -> dict | None:
        with self.transaccion() as conn:
            return conn.execute(sql, params).fetchone()

    def execute(self, sql: Any, params: Sequence | dict | None = None) -> int:
        with self.transaccion() as conn:
            return conn.execute(sql, params).rowcount

    def ejecutar_script(self, texto: str) -> None:
        """Ejecuta un script SQL completo (sin parámetros) en una sola transacción."""
        with self.transaccion() as conn:
            conn.execute(texto)
