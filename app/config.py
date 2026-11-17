"""Configuración centralizada: todo viene de variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Configuracion:
    entorno: str
    database_url: str
    secret_key: str
    jwt_secret: str
    jwt_expira_min: int
    cookie_segura: bool
    iva: float = 0.19
    dir_facturas: str = "facturas"
    filas_pdf_max: int = 5000
    cors_origenes: tuple[str, ...] = ()       # vacío = solo el mismo origen (no se emiten cabeceras CORS)
    login_por_minuto: int = 10
    registro_por_hora: int = 10

    @classmethod
    def desde_entorno(cls) -> Configuracion:
        def requerido(nombre: str) -> str:
            valor = os.environ.get(nombre, "").strip()
            if not valor:
                raise RuntimeError(f"Falta la variable de entorno {nombre} (revisa .env.example)")
            return valor

        secret, jwt_secret = requerido("SECRET_KEY"), requerido("JWT_SECRET_KEY")
        if len(secret) < 32 or len(jwt_secret) < 32:
            raise RuntimeError("SECRET_KEY y JWT_SECRET_KEY deben tener al menos 32 caracteres")
        return cls(
            entorno=os.environ.get("FLASK_ENV", "production"),
            database_url=requerido("DATABASE_URL"),
            secret_key=secret,
            jwt_secret=jwt_secret,
            jwt_expira_min=int(os.environ.get("JWT_EXPIRA_MINUTOS", "120")),
            cookie_segura=os.environ.get("COOKIE_SEGURA", "false").lower() == "true",
            iva=float(os.environ.get("IVA", "0.19")),
            # Ruta ABSOLUTA: send_file resuelve rutas relativas contra app/ y no contra el directorio de trabajo
            dir_facturas=os.path.abspath(os.environ.get("DIR_FACTURAS", "facturas")),
            cors_origenes=_origenes(os.environ.get("CORS_ORIGENES", "")),
            login_por_minuto=int(os.environ.get("LIMITE_LOGIN_POR_MINUTO", "10")),
            registro_por_hora=int(os.environ.get("LIMITE_REGISTRO_POR_HORA", "10")),
        )


def _origenes(texto: str) -> tuple[str, ...]:
    """Lista blanca explícita de orígenes CORS. '*' no se admite porque la API usa cookies de sesión."""
    origenes = tuple(o.strip().rstrip("/") for o in texto.split(",") if o.strip())
    if "*" in origenes:
        raise RuntimeError("CORS_ORIGENES no admite '*': lista los orígenes permitidos (https://dominio)")
    for o in origenes:
        if not o.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise RuntimeError(f"Origen CORS inválido o inseguro: {o}")
    return origenes
