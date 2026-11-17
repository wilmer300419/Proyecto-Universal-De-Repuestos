"""Uso:  python -m migraciones [migrar|estado|revertir [N]]"""
import os
import sys

from dotenv import load_dotenv

from . import EjecutorMigraciones


def main(argv: list[str]) -> int:
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("Define DATABASE_URL (ver .env.example)")
        return 2
    ejecutor = EjecutorMigraciones(dsn)
    comando = argv[0] if argv else "migrar"
    if comando == "migrar":
        print("Aplicadas:", ", ".join(ejecutor.migrar()) or "ninguna (al día)")
    elif comando == "estado":
        for e in ejecutor.estado():
            print(f"{e.version}  {'aplicada ' if e.aplicada else 'PENDIENTE'}  {e.nombre}" + ("" if e.checksum_ok else "  ¡MODIFICADA!"))
    elif comando == "revertir":
        print("Revertidas:", ", ".join(ejecutor.revertir(int(argv[1]) if len(argv) > 1 else 1)) or "ninguna")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
