"""Seed idempotente: upsert de 9 usuarios + 3 grupos padres (espejo del seed EF).

Uso desde backend-fastapi/:  python scripts/seed.py
Requiere .env con DATABASE_URL, JWT_SECRET y SEED_PASSWORD.
Nunca borra; solo inserta o actualiza por PK (RN-S1-02).
"""

import os
import sys
from datetime import datetime, timezone

import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.grupo_padre import GrupoPadre
from app.models.usuario import Usuario

USUARIOS = [
    (1, "mattias.ribera@upds.edu.bo", "Mattias Ribera Rojas", "Tecnico", True),
    (2, "diego.orihuela@upds.edu.bo", "Diego Orihuela Herrera", "Tecnico", False),
    (3, "paul.quispe@upds.edu.bo", "Paul Manuel Quispe Choque", "Tecnico", False),
    (4, "jose.orihuela@upds.edu.bo", "Jose Maria Orihuela Herrera", "Tecnico", False),
    (5, "sally.aparicio@upds.edu.bo", "Sally Aparicio", "Tecnico", False),
    (6, "carolina.ataides@upds.edu.bo", "Ana Carolina Ataides", "Tecnico", False),
    (7, "samira.barrientos@upds.edu.bo", "Samira Barrientos", "Tecnico", False),
    (8, "josue.huayllas@upds.edu.bo", "Josue Huayllas", "Jefe", False),
    (9, "wilmer.cerruto@upds.edu.bo", "Wilmer Cerruto", "Jefe", False),
]

PADRES = [
    (1, "Administrativos", 1),
    (2, "Académicos", 2),
    (3, "Extras", 3),
]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def run_seed() -> dict[str, int]:
    password = os.getenv("SEED_PASSWORD")
    if not password:
        raise RuntimeError("Falta SEED_PASSWORD")
    now = datetime.now(timezone.utc)
    hashed = hash_password(password)
    stats = {"usuarios_insertados": 0, "usuarios_actualizados": 0, "padres": 0}
    with SessionLocal() as db:
        for uid, email, name, role, can_view in USUARIOS:
            u = db.get(Usuario, uid)
            if u is None:
                db.add(
                    Usuario(
                        id=uid,
                        email=email,
                        password_hash=hashed,
                        display_name=name,
                        role=role,
                        estado_actual="Ausente",
                        can_view_dashboard=can_view,
                        created_at=now,
                        updated_at=now,
                    )
                )
                stats["usuarios_insertados"] += 1
            else:
                u.email = email
                u.password_hash = hashed
                u.display_name = name
                u.role = role
                u.can_view_dashboard = can_view
                u.updated_at = now
                stats["usuarios_actualizados"] += 1
        for pid, nombre, orden in PADRES:
            if db.get(GrupoPadre, pid) is None:
                db.add(GrupoPadre(id=pid, nombre=nombre, orden=orden))
                stats["padres"] += 1
        db.commit()
    return stats


if __name__ == "__main__":
    print(run_seed())
