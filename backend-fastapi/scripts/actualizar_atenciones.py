"""Suma a la base las atenciones que el CSV tenga de mas (prod sigue registrando).

Uso desde backend-fastapi/:
    python scripts/extraer_septiembre.py     # refresca el CSV desde prod
    python scripts/actualizar_atenciones.py  # aplica lo que falte

Por que no alcanza con seed.py: ese re-hashea la contrasena de todos los usuarios.
Para sumar atenciones no hace falta tocar credenciales.

Idempotente: se puede correr las veces que haga falta.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from scripts.seed import seed_atenciones


def main() -> int:
    with SessionLocal() as db:
        stats = seed_atenciones(db)
        db.commit()
    nuevas = stats["atenciones"]
    print(f"atenciones nuevas: {nuevas}")
    if nuevas:
        print(f"  con colaborador: {stats['con_colaborador']}")
        print(f"  fuera de turno : {stats['fuera_de_turno']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
