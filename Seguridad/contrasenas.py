"""Política y cifrado de contraseñas (hash scrypt con sal, vía werkzeug)."""
from __future__ import annotations

import re
import secrets

from werkzeug.security import check_password_hash, generate_password_hash


class PoliticaContrasena:
    MINIMO = 10

    def validar(self, clave: str, nombre_usuario: str = "") -> list[str]:
        errores = []
        if len(clave) < self.MINIMO:
            errores.append(f"Debe tener al menos {self.MINIMO} caracteres.")
        if not re.search(r"[a-z]", clave):
            errores.append("Debe incluir una letra minúscula.")
        if not re.search(r"[A-Z]", clave):
            errores.append("Debe incluir una letra mayúscula.")
        if not re.search(r"\d", clave):
            errores.append("Debe incluir un número.")
        if not re.search(r"[^\w\s]", clave):
            errores.append("Debe incluir un símbolo (por ejemplo ! # $ %).")
        if nombre_usuario and nombre_usuario.lower() in clave.lower():
            errores.append("No debe contener el nombre de usuario.")
        return errores


class HasherContrasena:
    def __init__(self) -> None:
        # Hash señuelo: permite gastar el mismo tiempo cuando el usuario no existe
        # y así no revelar (por tiempo de respuesta) qué usuarios están registrados.
        self._senuelo = generate_password_hash(secrets.token_urlsafe(16))

    def cifrar(self, clave: str) -> str:
        return generate_password_hash(clave)

    def verificar(self, hash_guardado: str, clave: str) -> bool:
        return check_password_hash(hash_guardado, clave)

    def verificar_senuelo(self, clave: str) -> None:
        check_password_hash(self._senuelo, clave)
