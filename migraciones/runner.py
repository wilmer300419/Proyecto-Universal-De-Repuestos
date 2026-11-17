"""Ejecutor de migraciones.

Convención de archivos en ``versions/``:
    V001__descripcion.up.sql    -> aplica el cambio
    V001__descripcion.down.sql  -> lo revierte

Cada migración corre en su propia transacción. El estado se guarda en la tabla
``schema_migrations`` junto con un checksum para detectar archivos modificados.
Todas las tablas viven en el esquema ``automotriz`` (se fija en el search_path de la conexión).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

_PATRON = re.compile(r"^(V\d+)__(.+)\.(up|down)\.sql$")
_DIR_POR_DEFECTO = Path(__file__).parent / "versions"
ESQUEMA = "automotriz"
OPCIONES_CONEXION = f"-c search_path={ESQUEMA},public -c timezone=America/Bogota"


@dataclass(frozen=True)
class EstadoMigracion:
    version: str
    nombre: str
    aplicada: bool
    checksum_ok: bool = True


@dataclass(frozen=True)
class _Archivo:
    version: str
    nombre: str
    up: Path
    down: Path | None


class EjecutorMigraciones:
    def __init__(self, dsn: str, directorio: Path | None = None):
        self._dsn = dsn
        self._dir = Path(directorio) if directorio else _DIR_POR_DEFECTO

    # ------------------------------------------------------------ utilidades
    @staticmethod
    def _checksum(ruta: Path) -> str:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()

    def _descubrir(self) -> list[_Archivo]:
        ups, downs = {}, {}
        for ruta in sorted(self._dir.glob("V*.sql")):
            m = _PATRON.match(ruta.name)
            if not m:
                continue
            version, nombre, sentido = m.groups()
            (ups if sentido == "up" else downs)[version] = (nombre, ruta)
        return [_Archivo(v, ups[v][0], ups[v][1], downs.get(v, (None, None))[1]) for v in sorted(ups)]

    def _conectar(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, options=OPCIONES_CONEXION)

    def _asegurar_tabla(self, conn: psycopg.Connection) -> None:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version     VARCHAR(20) PRIMARY KEY,
                   nombre      VARCHAR(120) NOT NULL,
                   checksum    CHAR(64) NOT NULL,
                   aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        conn.commit()

    def _aplicadas(self, conn: psycopg.Connection) -> dict[str, str]:
        return dict(conn.execute("SELECT version, checksum FROM schema_migrations").fetchall())

    # ------------------------------------------------------------ operaciones
    def estado(self) -> list[EstadoMigracion]:
        with self._conectar() as conn:
            self._asegurar_tabla(conn)
            aplicadas = self._aplicadas(conn)
        salida = []
        for a in self._descubrir():
            hecho = a.version in aplicadas
            salida.append(EstadoMigracion(a.version, a.nombre, hecho,
                                          (not hecho) or aplicadas[a.version] == self._checksum(a.up)))
        return salida

    def migrar(self) -> list[str]:
        """Aplica todas las migraciones pendientes. Devuelve las versiones aplicadas."""
        nuevas = []
        with self._conectar() as conn:
            self._asegurar_tabla(conn)
            aplicadas = self._aplicadas(conn)
            for a in self._descubrir():
                if a.version in aplicadas:
                    if aplicadas[a.version] != self._checksum(a.up):
                        raise RuntimeError(f"La migración {a.version} ya aplicada fue modificada; crea una nueva versión.")
                    continue
                with conn.transaction():
                    conn.execute(a.up.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migrations (version, nombre, checksum) VALUES (%s,%s,%s)",
                                 (a.version, a.nombre, self._checksum(a.up)))
                nuevas.append(a.version)
        return nuevas

    def revertir(self, pasos: int = 1) -> list[str]:
        """Revierte las últimas *pasos* migraciones aplicadas (en orden inverso)."""
        revertidas = []
        with self._conectar() as conn:
            self._asegurar_tabla(conn)
            aplicadas = self._aplicadas(conn)
            por_version = {a.version: a for a in self._descubrir()}
            for version in sorted(aplicadas, reverse=True)[:pasos]:
                a = por_version.get(version)
                if a is None or a.down is None:
                    raise RuntimeError(f"La migración {version} no tiene archivo .down.sql")
                with conn.transaction():
                    conn.execute(a.down.read_text(encoding="utf-8"))
                    conn.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
                revertidas.append(version)
        return revertidas

    def revertir_todo(self) -> list[str]:
        with self._conectar() as conn:
            self._asegurar_tabla(conn)
            n = len(self._aplicadas(conn))
        return self.revertir(n) if n else []
