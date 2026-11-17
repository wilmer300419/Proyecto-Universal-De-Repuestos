"""Calcula el Mutation Score a partir de la caché de mutmut 2.x (.mutmut-cache, SQLite) y falla si es menor
que el umbral.  Uso:  python tools/mutation_score.py --umbral 50 [--objetivo 60]

Score = mutantes eliminados (incluye timeouts) / mutantes evaluados (eliminados + sobrevivientes + sospechosos).
Los mutantes 'skipped' y 'untested' no cuentan.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ELIMINADOS = {"ok_killed", "bad_timeout"}
EVALUADOS = ELIMINADOS | {"bad_survived", "ok_suspicious"}


def calcular(cache: Path) -> dict:
    if not cache.exists():
        raise SystemExit(f"No existe {cache}: ejecuta primero `mutmut run`.")
    with sqlite3.connect(cache) as conn:
        conteo = dict(conn.execute("SELECT status, COUNT(*) FROM Mutant GROUP BY status").fetchall())
    eliminados = sum(conteo.get(s, 0) for s in ELIMINADOS)
    evaluados = sum(conteo.get(s, 0) for s in EVALUADOS)
    score = 100.0 * eliminados / evaluados if evaluados else 0.0
    return {"por_estado": conteo, "eliminados": eliminados, "evaluados": evaluados, "score": round(score, 2)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=".mutmut-cache")
    ap.add_argument("--umbral", type=float, default=50.0, help="el proceso falla por debajo de este valor")
    ap.add_argument("--objetivo", type=float, default=60.0, help="meta informativa")
    ap.add_argument("--salida", default="mutation-report.json")
    args = ap.parse_args(argv)
    r = calcular(Path(args.cache))
    Path(args.salida).write_text(json.dumps(r, indent=2), encoding="utf-8")
    print(f"Mutation Score: {r['score']}% ({r['eliminados']}/{r['evaluados']}) · estados: {r['por_estado']}")
    if r["evaluados"] == 0:
        print("::error::mutmut no evaluó ningún mutante")
        return 1
    if r["score"] < args.umbral:
        print(f"::error::Mutation Score {r['score']}% < umbral {args.umbral}%")
        return 1
    if r["score"] < args.objetivo:
        print(f"::warning::Mutation Score {r['score']}% por debajo del objetivo {args.objetivo}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
