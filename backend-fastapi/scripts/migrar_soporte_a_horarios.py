"""Cutover: move the old Soporte lab data onto the horarios tables (task M6).

Usage from backend-fastapi/ (or /app in the api container), AFTER
`alembic upgrade head` (needs migration 0029):

    python scripts/migrar_soporte_a_horarios.py                 # dry-run (default)
    python scripts/migrar_soporte_a_horarios.py --reporte /tmp/m6.csv
    python scripts/migrar_soporte_a_horarios.py --apply --reporte /tmp/m6.json

Dry-run only reads and prints what would move plus the review report. --apply
writes everything in ONE transaction (all or nothing). Re-running is safe:
migrated source rows are tracked in `horarios.migracion_origen`.

Writes to whichever DB DATABASE_URL points to; the target is printed first.
Logic and the field mapping live in `app/services/migracion_soporte.py`.
"""

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine
from app.services.migracion_soporte import Resultado, escribir_reporte, migrar

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _imprimir(res: Resultado) -> None:
    modo = "APLICADO" if res.aplicado else "DRY-RUN (nada escrito)"
    print(f"\n== {modo} ==")
    for clave in sorted(res.conteos):
        print(f"  {clave}: {res.conteos[clave]}")
    motivos = Counter((i.seccion, i.motivo) for i in res.incidencias)
    print(f"\n== Para revisar: {len(res.incidencias)} filas ==")
    for (seccion, motivo), total in sorted(motivos.items()):
        print(f"  {seccion} · {motivo}: {total}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--dry-run", action="store_true", help="solo leer (por defecto)")
    modo.add_argument(
        "--apply", action="store_true", help="escribir en una transacción"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR, help="carpeta de los JSON"
    )
    parser.add_argument("--reporte", type=Path, help="ruta del reporte (.csv o .json)")
    args = parser.parse_args()

    url = engine.url
    print(f"Base: {url.host}:{url.port}/{url.database} · datos: {args.data_dir}")
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            res = migrar(conn, data_dir=args.data_dir, aplicar=args.apply)
        except Exception:
            tx.rollback()
            raise
        if args.apply:
            tx.commit()
        else:
            tx.rollback()
    _imprimir(res)
    if args.reporte:
        print(f"\nReporte: {escribir_reporte(res, args.reporte)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
