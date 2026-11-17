"""Reglas de dependencia del MVC: el modelo no conoce Flask ni el driver; Seguridad no conoce la aplicación."""
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _importa(ruta: pathlib.Path, patron: str) -> bool:
    return re.search(rf"^\s*(from|import)\s+({patron})\b", ruta.read_text(encoding="utf-8"), re.M) is not None


def test_modelo_puro():
    for f in (RAIZ / "app" / "models").rglob("*.py"):
        assert not _importa(f, r"flask|psycopg|psycopg_pool|werkzeug"), f"{f.name} importa infraestructura"


def test_seguridad_autonoma():
    for f in (RAIZ / "Seguridad").rglob("*.py"):
        assert not _importa(f, r"app(\.\w+)*|\.\.app"), f"Seguridad/{f.name} importa el paquete app"


def test_controladores_sin_sql():
    for f in (RAIZ / "app" / "controllers").rglob("*.py"):
        texto = f.read_text(encoding="utf-8")
        assert not re.search(r"\b(SELECT\s.+\sFROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", texto), f"{f.name} contiene SQL"
