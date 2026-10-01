"""Idempotent seed for laboratorios service: 10 labs + 4 categories.

Usage from backend-fastapi/:  python scripts/seed_laboratorios.py
Requires .env with DATABASE_URL. Requires migration 0011 applied.
Never deletes; upserts by codigo (labs) and normalized nombre (categories),
so re-running is safe. Writes to whichever DB DATABASE_URL points to —
double-check it before running (never run against production by accident).
"""

import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.laboratorio import LabCategoria, Laboratorio

LABORATORIOS = [(f"LAB-{i:02d}", f"TBD-{i:02d}") for i in range(1, 11)]
CATEGORIAS = (
    "Mantenimiento preventivo",
    "Mantenimiento correctivo",
    "Calibración",
    "Otros",
)


def main() -> None:
    ahora = datetime.now(UTC)
    with SessionLocal() as db:
        for codigo, nombre in LABORATORIOS:
            lab = db.scalar(select(Laboratorio).where(Laboratorio.codigo == codigo))
            if lab is None:
                db.add(
                    Laboratorio(
                        codigo=codigo, nombre=nombre, activa=True, created_at=ahora
                    )
                )
            elif not lab.activa or lab.nombre != nombre:
                lab.nombre = nombre
                lab.activa = True
        existentes = {
            (c.nombre or "").strip().lower(): c
            for c in db.scalars(select(LabCategoria)).all()
        }
        for nombre in CATEGORIAS:
            cat = existentes.get(nombre.strip().lower())
            if cat is None:
                db.add(LabCategoria(nombre=nombre, activa=True, created_at=ahora))
            elif not cat.activa:
                cat.activa = True
        db.commit()
    print(f"OK: {len(LABORATORIOS)} laboratorios, {len(CATEGORIAS)} categorias.")


if __name__ == "__main__":
    main()
