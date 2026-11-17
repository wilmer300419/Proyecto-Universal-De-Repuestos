"""Pruebas. Las de integración usan TEST_DATABASE_URL (una base EXCLUSIVA para pruebas: se borra y se recrea
con las migraciones y sql/datos_prueba.sql) y se omiten si no está definida."""
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("SECRET_KEY", "x" * 48)
os.environ.setdefault("JWT_SECRET_KEY", "y" * 48)
CLAVE = "Repuestos#2026"


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Defina TEST_DATABASE_URL para ejecutar las pruebas de integración")
    os.environ["DATABASE_URL"] = dsn
    os.environ["DIR_FACTURAS"] = str(tmp_path_factory.mktemp("facturas"))
    from migraciones import EjecutorMigraciones
    ejecutor = EjecutorMigraciones(dsn)
    ejecutor.revertir_todo()
    ejecutor.migrar()
    from app import crear_app
    aplicacion = crear_app()
    aplicacion.extensions["db"].ejecutar_script((RAIZ / "sql" / "datos_prueba.sql").read_text(encoding="utf-8"))
    return aplicacion


def _cliente(app, usuario):
    from ayudas import iniciar_sesion
    c = app.test_client()
    r = iniciar_sesion(app, c, usuario, CLAVE)
    assert r.status_code == 200, r.get_json()
    c.csrf = r.get_json()["csrf_token"]
    return c


@pytest.fixture()
def admin(app):
    return _cliente(app, "admin")


@pytest.fixture()
def cliente(app):
    return _cliente(app, "lhernandez")


@pytest.fixture()
def empacador(app):
    return _cliente(app, "pmartinez")


@pytest.fixture()
def repartidor(app):
    return _cliente(app, "dmoreno")


@pytest.fixture(autouse=True)
def _limitador_limpio(request):
    """Aislamiento: cada prueba empieza con el contador de intentos por IP en cero (todas usan 127.0.0.1).
    El límite NO se desactiva; test_seguridad.py prueba que responde 429."""
    if "app" in request.fixturenames:
        request.getfixturevalue("app").extensions["limitador"].reiniciar()
