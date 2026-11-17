"""Servicio CRUD de catálogos: validación/conversión según los metadatos + reglas + auditoría."""
from __future__ import annotations

from collections.abc import Mapping

from psycopg import errors as pgerr

from Seguridad.repositorio import RepositorioAuditoria

from ..core.database import Database
from ..models.errores import ErrorDeNegocio, ErrorValidacion, NoEncontrado
from ..models.meta import Campo, Entidad
from ..models.validacion import a_booleano, a_entero
from ..repositories.crud import RepositorioCrud


class ServicioCrud:
    def __init__(self, db: Database, auditoria: RepositorioAuditoria):
        self._db, self._auditoria = db, auditoria

    def repo(self, e: Entidad) -> RepositorioCrud:
        return RepositorioCrud(self._db, e)

    # ----------------------------------------------------------- consulta
    def listar(self, e: Entidad, args: Mapping[str, str]) -> list[dict]:
        filtros = {}
        for nombre, valor in args.items():                   # solo columnas declaradas (lista blanca)
            campo = e.campo(nombre) or (Campo(e.pk, "ID", "entero") if nombre == e.pk else None)
            if campo is not None and str(valor).strip() != "":
                try:
                    filtros[nombre] = self._convertir(campo, valor)
                except ValueError as exc:            # antes: ValueError sin capturar -> HTTP 500
                    raise ErrorValidacion(f"Filtro {nombre}: {exc}") from None
        return self.repo(e).listar(filtros)

    def obtener(self, e: Entidad, pk: int) -> dict:
        return self.repo(e).obtener(pk) or self._no_existe(e)

    # ----------------------------------------------------------- validación
    def validar(self, e: Entidad, datos: Mapping, parcial: bool = False) -> dict:
        limpios, errores = {}, {}
        for c in e.campos:
            if c.nombre not in datos:
                if not parcial:
                    if c.requerido:
                        errores[c.nombre] = f"{c.etiqueta}: este campo es obligatorio."
                    elif c.por_defecto is not None:
                        limpios[c.nombre] = c.por_defecto
                continue
            try:
                limpios[c.nombre] = self._convertir(c, datos[c.nombre])
            except ValueError as exc:
                errores[c.nombre] = f"{c.etiqueta}: {exc}"
        if errores:
            raise ErrorValidacion(" ".join(errores.values()), errores)
        return limpios

    @staticmethod
    def _convertir(c: Campo, valor):
        """Convierte un valor según el tipo del campo. Lanza ValueError con un mensaje para el usuario."""
        vacio = valor is None or (isinstance(valor, str) and not valor.strip())
        if vacio:
            if c.requerido:
                raise ValueError("este campo es obligatorio.")
            return c.por_defecto            # p. ej. state vacío -> TRUE (la columna es NOT NULL)
        try:
            if c.tipo == "booleano":
                return a_booleano(valor, c.etiqueta)
            if c.tipo in ("entero", "fk"):
                return a_entero(valor, c.etiqueta, c.minimo)
        except ErrorValidacion as exc:
            raise ValueError(exc.mensaje) from None
        limpio = str(valor).strip()
        if c.max_len and len(limpio) > c.max_len:
            raise ValueError(f"máximo {c.max_len} caracteres.")
        return limpio

    # ------------------------------------------------------------ operaciones
    def crear(self, e: Entidad, datos: Mapping, usuario, ip: str | None) -> dict:
        fila = self._proteger(lambda: self.repo(e).crear(self.validar(e, datos)), e)
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "CREAR", e.slug, f"{e.pk}={fila[e.pk]}", ip)
        return fila

    def actualizar(self, e: Entidad, pk: int, datos: Mapping, usuario, ip: str | None) -> dict:
        self._verificar_protegido(e, pk)
        fila = self._proteger(lambda: self.repo(e).actualizar(pk, self.validar(e, datos, parcial=True)), e)
        if fila is None:
            self._no_existe(e)
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "ACTUALIZAR", e.slug, f"{e.pk}={pk}", ip)
        return fila

    def eliminar(self, e: Entidad, pk: int, usuario, ip: str | None) -> None:
        self._verificar_protegido(e, pk)
        if not self._proteger(lambda: self.repo(e).eliminar(pk), e):
            self._no_existe(e)
        self._auditoria.registrar(usuario.id, usuario.nombre_usuario, "ELIMINAR", e.slug, f"{e.pk}={pk}", ip)

    @staticmethod
    def _verificar_protegido(e: Entidad, pk: int) -> None:
        if pk in e.ids_protegidos:
            raise ErrorDeNegocio(f"Este registro de {e.singular} lo usa el sistema y no se puede modificar.")

    @staticmethod
    def _no_existe(e: Entidad):
        raise NoEncontrado(f"No existe ese registro de {e.singular}.")

    @staticmethod
    def _proteger(accion, e: Entidad):
        try:
            return accion()
        except pgerr.UniqueViolation:
            raise ErrorDeNegocio(f"Ya existe un registro de {e.singular} con esos datos.") from None
        except pgerr.ForeignKeyViolation:
            raise ErrorDeNegocio("No se puede completar: el registro está relacionado con otros datos "
                                 "(o hace referencia a un valor que no existe).") from None
        except (pgerr.CheckViolation, pgerr.NotNullViolation):
            raise ErrorDeNegocio("Algún valor no cumple las reglas de validación de la base de datos.") from None
