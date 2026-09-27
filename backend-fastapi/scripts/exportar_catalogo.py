"""Vuelca el catalogo de la BD a mapeo-areas-dedup.csv (con codigos).

Uso desde backend-fastapi/:  python scripts/exportar_catalogo.py

Es la inversa de seed_catalogo(): despues de renombrar o mover nodos en /jerarquia,
este script vuelca la estructura real (con los codigos estables) al CSV. Asi el CSV
siempre refleja la jerarquia actual y un seed sobre una BD vacia la reproduce.

Solo lectura: no escribe nada en la BD.
"""

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.db.base import SessionLocal
from app.models.area import Area
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "mapeo-areas-dedup.csv"


def main() -> int:
    with SessionLocal() as db:
        padres = {
            g.id: (g.codigo, g.nombre, g.orden)
            for g in db.scalars(select(GrupoPadre)).all()
        }
        grupos = {g.id: (g.codigo, g.nombre) for g in db.scalars(select(Grupo)).all()}
        areas = list(db.scalars(select(Area)).all())

    orden = {codigo: o for codigo, _, o in padres.values()}
    filas = sorted(
        [
            (
                padres[a.grupo_padre_id][0],
                grupos[a.grupo_id][0] if a.grupo_id is not None else "",
                a.codigo,
                a.nombre,
                grupos[a.grupo_id][1] if a.grupo_id is not None else "",
                "1" if a.activo else "0",
            )
            for a in areas
            if a.grupo_padre_id in padres
            and (a.grupo_id is None or a.grupo_id in grupos)
        ],
        key=lambda f: (orden.get(f[0], 99), f[1], f[3]),
    )

    with open(SALIDA, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, lineterminator="\r\n")
        escritor.writerow(
            [
                "codigo_padre",
                "codigo_grupo",
                "codigo_area",
                "nombre",
                "nombre_grupo",
                "activo",
            ]
        )
        escritor.writerows(filas)

    print(f"escrito: {SALIDA.name} ({len(filas)} areas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
