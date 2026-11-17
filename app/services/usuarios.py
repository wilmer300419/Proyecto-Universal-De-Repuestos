"""Servicio de usuarios: registro de clientes, alta de personal y administración de cuentas.

La persona (tabla ``person``) y su usuario (``app_user``) se crean en la MISMA transacción;
la seguridad (política de contraseñas, hash, sesiones) la aporta el paquete ``Seguridad``.
"""
from __future__ import annotations

import re

from psycopg import errors as pgerr

from Seguridad import PERSONAL, Rol, Usuario
from Seguridad.repositorio import RepositorioAuditoria, RepositorioUsuarios
from Seguridad.servicio import DatosUsuarioInvalidos, ServicioAutenticacion

from ..core.database import Database
from ..models.errores import ErrorDeNegocio, ErrorValidacion, NoEncontrado
from ..models.validacion import a_booleano, a_entero
from ..repositories.ventas import RepositorioPersonas
from ..utils.fechas import parsear_fecha

_TEXTO = {"first_name": 100, "second_name": 100, "last_name": 100, "second_last_name": 100, "identification": 30,
          "phone_number": 30}


class ServicioUsuarios:
    def __init__(self, db: Database, seguridad: ServicioAutenticacion):
        self._db, self._seg = db, seguridad

    def _persona(self, d: dict, email: str) -> dict:
        p = {}
        for campo, maximo in _TEXTO.items():
            valor = str(d.get(campo) or "").strip()
            if len(valor) > maximo:
                raise ErrorValidacion(f"{campo}: máximo {maximo} caracteres")
            p[campo] = valor or None
        for campo, etiqueta in (("first_name", "El nombre"), ("last_name", "El apellido"), ("identification", "El documento")):
            if not p[campo]:
                raise ErrorValidacion(f"{etiqueta} es obligatorio")
        if not re.fullmatch(r"[0-9A-Za-z-]{4,30}", p["identification"]):
            raise ErrorValidacion("El documento solo admite letras, números y guiones (4 a 30 caracteres)")
        p["document_type_id"] = a_entero(d.get("document_type_id"), "El tipo de documento", 1)
        p["city_id"] = a_entero(d.get("city_id"), "La ciudad", 1)
        p["birth_date"] = parsear_fecha(d.get("birth_date"))
        p["email"] = email
        return p

    def _crear(self, d: dict, rol: Rol, autor: Usuario | None, ip) -> dict:
        nombre = str(d.get("username") or "").strip().lower()
        email = str(d.get("email") or "").strip().lower()
        clave = str(d.get("password") or "")
        persona = self._persona(d, email)
        try:
            with self._db.unidad_de_trabajo() as tx:
                usuarios, personas = RepositorioUsuarios(tx), RepositorioPersonas(tx)
                self._seg.verificar_disponible(nombre, email, clave, usuarios)        # antes de crear la persona
                if personas.identificacion_existe(persona["identification"]):
                    raise ErrorDeNegocio("Ese número de documento ya está registrado")
                if not personas.existe("city", persona["city_id"]) or not personas.existe("document_type", persona["document_type_id"]):
                    raise ErrorValidacion("La ciudad o el tipo de documento no son válidos")
                id_persona = personas.crear(persona)
                user_id = self._seg.crear_usuario(nombre, email, clave, rol, id_persona, usuarios)
                RepositorioAuditoria(tx).registrar(autor.id if autor else user_id, autor.nombre_usuario if autor else nombre,
                                                   "CREAR", "usuario", f"{nombre} ({rol.value})", ip)
        except DatosUsuarioInvalidos as exc:
            raise ErrorValidacion(exc.mensaje(), {k: " ".join(v) for k, v in exc.errores.items()}) from None
        except pgerr.UniqueViolation:
            raise ErrorDeNegocio("El usuario, el correo o el documento ya están registrados") from None
        return {"user_id": user_id, "username": nombre, "email": email, "role": rol.value}

    def registrar_cliente(self, d: dict, ip) -> dict:
        return self._crear(d, Rol.CLIENTE, None, ip)

    def crear_personal(self, d: dict, autor: Usuario, ip) -> dict:
        try:
            rol = Rol(str(d.get("role") or ""))
        except ValueError:
            raise ErrorValidacion(f"role debe ser uno de: {', '.join(r.value for r in Rol)}") from None
        return self._crear(d, rol, autor, ip)

    def listar(self, rol: str | None = None) -> list[dict]:
        return self._seg.usuarios.listar(rol or None)

    def actualizar(self, user_id: int, d: dict, autor: Usuario, ip) -> dict:
        u = self._seg.usuarios.buscar_por_id(user_id) or self._no_existe()
        try:
            rol = Rol(d.get("role", u.rol.value))
        except ValueError:
            raise ErrorValidacion("Rol inválido") from None
        activo = a_booleano(d.get("status", u.activo), "status")      # antes bool("false") == True
        if u.id == autor.id and (rol is not u.rol or not activo):
            raise ErrorDeNegocio("No puedes quitarte tu propio rol ni desactivar tu propia cuenta")
        self._seg.usuarios.actualizar(u.id, rol, activo)
        if rol is not u.rol or not activo:            # cambiar el rol o desactivar invalida las sesiones abiertas
            self._seg.cerrar_todas(u.id, u.nombre_usuario, "CAMBIO_ESTADO_O_ROL", ip)
        if d.get("password"):
            try:
                self._seg.cambiar_password(u.id, u.nombre_usuario, str(d["password"]))
            except DatosUsuarioInvalidos as exc:
                raise ErrorValidacion(exc.mensaje()) from None
        self._seg.auditoria.registrar(autor.id, autor.nombre_usuario, "ACTUALIZAR", "usuario",
                                      f"{u.nombre_usuario} rol={rol.value} activo={activo}", ip)
        return next(f for f in self.listar() if f["user_id"] == u.id)

    def cerrar_sesiones(self, user_id: int, autor: Usuario, ip) -> int:
        u = self._seg.usuarios.buscar_por_id(user_id) or self._no_existe()
        return self._seg.cerrar_todas(u.id, u.nombre_usuario, f"FORZADO_POR_{autor.nombre_usuario}"[:40], ip)

    @staticmethod
    def _no_existe():
        raise NoEncontrado("Usuario no encontrado")


ROLES_PERSONAL = tuple(r.value for r in PERSONAL)
