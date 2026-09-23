"""Copia a esta base las contrasenas de la v1 (bcrypt, mismo algoritmo).

Uso desde backend-fastapi/ (con el .env cargado):
    python scripts/copiar_contrasenas_v1.py

Existe para el corte: la base de trabajo quedo con todos los usuarios usando la
contrasena del seed, y esto la reemplaza por la que cada uno ya venia usando en v1,
para que nadie tenga que cambiarla. No toca ninguna otra columna ni los ids.

Idempotente. Reporta los usuarios locales que no existen en v1 (por ejemplo el
auxiliar): esos quedan con la contrasena del seed y hay que decidir que hacer.
"""

import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.db.base import SessionLocal
from app.models.usuario import Usuario
from scripts.promover_a_produccion import usuarios_de_v1


def main() -> int:
    with SessionLocal() as db:
        print(f"base destino: {urlsplit(os.environ['DATABASE_URL']).path.lstrip('/')}")
        hashes = {f["Email"].strip().lower(): f["PasswordHash"].strip() for f in usuarios_de_v1()}
        copiados = 0
        sin_v1: list[str] = []
        for u in db.scalars(select(Usuario)).all():
            nuevo = hashes.get(u.email.strip().lower())
            if not nuevo:
                sin_v1.append(u.email)
                continue
            if u.password_hash == nuevo:
                continue
            u.password_hash = nuevo
            copiados += 1
        db.commit()
        print(f"contrasenas actualizadas: {copiados}")
        for email in sin_v1:
            print(f"  AVISO: {email} no existe en v1, sigue con la del seed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
