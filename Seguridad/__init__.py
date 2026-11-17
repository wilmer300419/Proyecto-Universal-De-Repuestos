"""Paquete de Seguridad: autenticación JWT con sesiones en base de datos, contraseñas, CAPTCHA, roles,
CSRF y auditoría.

Es autónomo: solo necesita un objeto ``db`` con ``fetch_one / fetch_all / execute``
(ver ``contratos.EjecutorSQL``). No importa nada del paquete ``app``.
"""
from .configuracion import ConfigSeguridad
from .decoradores import grupo_requerido, login_requerido, rol_requerido, usuario_actual
from .flask_integracion import inicializar_seguridad
from .modelos import PERSONAL, Grupo, Rol, Usuario

__all__ = ["ConfigSeguridad", "inicializar_seguridad", "login_requerido", "rol_requerido", "grupo_requerido",
           "usuario_actual", "Rol", "Grupo", "Usuario", "PERSONAL"]
