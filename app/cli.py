"""Comandos de consola:  flask --app run <comando>"""
from __future__ import annotations

import os
from pathlib import Path

import click
from flask import Flask

from Seguridad import PERSONAL, Rol
from migraciones import EjecutorMigraciones

from .models.errores import ErrorAplicacion

DATOS_PRUEBA = Path(__file__).resolve().parent.parent / "sql" / "datos_prueba.sql"


def registrar_comandos(app: Flask) -> None:
    _comandos_migracion(app)
    _comandos_datos(app)
    _comando_crear_usuario(app)


def _comandos_migracion(app: Flask) -> None:
    def ejecutor() -> EjecutorMigraciones:
        return EjecutorMigraciones(app.config["CFG"].database_url)

    @app.cli.command("migrar")
    def migrar():
        """Aplica las migraciones pendientes."""
        click.echo("Aplicadas: " + (", ".join(ejecutor().migrar()) or "ninguna (al día)"))

    @app.cli.command("estado-migraciones")
    def estado():
        for e in ejecutor().estado():
            aviso = "" if e.checksum_ok else "  ¡MODIFICADA!"
            click.echo(f"{e.version}  {'aplicada ' if e.aplicada else 'PENDIENTE'}  {e.nombre}{aviso}")

    @app.cli.command("revertir")
    @click.argument("pasos", default=1)
    def revertir(pasos):
        """Revierte las últimas N migraciones."""
        click.echo("Revertidas: " + (", ".join(ejecutor().revertir(pasos)) or "ninguna"))



def _cargar_script(app: Flask) -> None:
    app.extensions["db"].ejecutar_script(DATOS_PRUEBA.read_text(encoding="utf-8"))
    click.echo("Datos de prueba cargados. Contraseña de los usuarios de ejemplo: Repuestos#2026")


def _comandos_datos(app: Flask) -> None:
    @app.cli.command("cargar-datos")
    def cargar_datos():
        """Carga sql/datos_prueba.sql (>= 20 registros por tabla) en una base migrada y sin ventas."""
        db = app.extensions["db"]
        if db.fetch_one("SELECT COUNT(*) AS n FROM app_user")["n"]:
            raise click.ClickException("La base ya tiene usuarios; usa `flask --app run reiniciar-bd` para recrearla.")
        _cargar_script(app)

    @app.cli.command("reiniciar-bd")
    @click.confirmation_option(prompt="Se BORRARÁN todos los datos del esquema automotriz. ¿Continuar?")
    def reiniciar_bd():
        """Revierte todas las migraciones, las aplica de nuevo y carga los datos de prueba."""
        e = EjecutorMigraciones(app.config["CFG"].database_url)
        click.echo("Revertidas: " + (", ".join(e.revertir_todo()) or "ninguna"))
        click.echo("Aplicadas: " + ", ".join(e.migrar()))
        _cargar_script(app)


def _comando_crear_usuario(app: Flask) -> None:
    @app.cli.command("crear-usuario")
    @click.argument("username")
    @click.option("--rol", type=click.Choice([r.value for r in PERSONAL]), default=Rol.ADMINISTRADOR.value, show_default=True)
    @click.option("--email", prompt="Correo")
    @click.option("--nombre", prompt="Nombre")
    @click.option("--apellido", prompt="Apellido")
    @click.option("--documento", prompt="Número de documento")
    def crear_usuario(username, rol, email, nombre, apellido, documento):
        """Crea un usuario interno. La contraseña se pide oculta (o variable USUARIO_PASSWORD)."""
        clave = os.environ.get("USUARIO_PASSWORD") or click.prompt("Contraseña", hide_input=True, confirmation_prompt=True)
        db = app.extensions["db"]
        tipo = db.fetch_one("SELECT document_type_id FROM document_type ORDER BY 1 LIMIT 1")
        ciudad = db.fetch_one("SELECT city_id FROM city ORDER BY 1 LIMIT 1")
        if not tipo or not ciudad:
            raise click.ClickException("Primero carga los catálogos (flask --app run cargar-datos).")
        try:
            app.extensions["usuarios"].crear_personal(
                {"username": username, "email": email, "password": clave, "role": rol, "first_name": nombre,
                 "last_name": apellido, "identification": documento, "document_type_id": tipo["document_type_id"],
                 "city_id": ciudad["city_id"]}, None, None)
        except ErrorAplicacion as exc:
            raise click.ClickException(exc.mensaje) from exc
        click.echo("Usuario creado.")
