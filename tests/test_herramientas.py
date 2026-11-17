"""Pruebas de las herramientas de CI: el cálculo del Mutation Score y su umbral."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mutation_score  # noqa: E402


def _cache(tmp_path, estados):
    ruta = tmp_path / ".mutmut-cache"
    with sqlite3.connect(ruta) as c:
        c.execute("CREATE TABLE Mutant (id INTEGER PRIMARY KEY, status TEXT)")
        c.executemany("INSERT INTO Mutant (status) VALUES (?)", [(e,) for e in estados])
    return ruta


def test_score_cuenta_timeouts_como_eliminados_e_ignora_skipped(tmp_path):
    r = mutation_score.calcular(_cache(tmp_path, ["ok_killed"] * 5 + ["bad_timeout"] + ["bad_survived"] * 4 + ["skipped"] * 3))
    assert (r["eliminados"], r["evaluados"], r["score"]) == (6, 10, 60.0)


def test_umbral_hace_fallar_el_pipeline(tmp_path):
    bajo = _cache(tmp_path, ["ok_killed"] * 4 + ["bad_survived"] * 6)
    salida = str(tmp_path / "r.json")
    assert mutation_score.main(["--cache", str(bajo), "--umbral", "50", "--salida", salida]) == 1
    assert mutation_score.main(["--cache", str(bajo), "--umbral", "40", "--salida", salida]) == 0
    assert Path(salida).exists()


def test_sin_mutantes_evaluados_falla(tmp_path):
    vacio = _cache(tmp_path, ["untested"])
    assert mutation_score.main(["--cache", str(vacio), "--salida", str(tmp_path / "r.json")]) == 1
