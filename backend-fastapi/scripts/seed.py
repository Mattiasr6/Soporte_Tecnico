"""Seed idempotente: 10 usuarios + 3 grupos padres + catalogo de areas + atenciones.

Uso desde backend-fastapi/:  python scripts/seed.py
Requiere .env con DATABASE_URL, JWT_SECRET y SEED_PASSWORD.
Requiere haber creado el esquema antes: alembic upgrade head.

Nunca borra; solo inserta o actualiza (RN-S1-02). Las atenciones se cargan de forma
incremental (idempotente por created_at), asi que re-correrlo trae lo nuevo sin duplicar.

Ojo: este seed re-hashea la contrasena de todos los usuarios. Para sumar solo las
atenciones nuevas de prod esta scripts/actualizar_atenciones.py.

El catalogo y las atenciones salen de los CSV de la raiz del repo, que se regeneran
con scripts/extraer_septiembre.py (prod sigue recibiendo atenciones todos los dias).
"""

import csv
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import bcrypt
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.area import Area
from app.models.atencion import Atencion
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre
from app.models.usuario import Usuario
from app.services.slugs import codigo_unico, slugify

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO_CSV = RAIZ / "mapeo-areas-dedup.csv"
ATENCIONES_CSV = RAIZ / "atenciones_septiembre.csv"

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
    (10, "auxiliar.soporte@upds.edu.bo", "Auxiliar Soporte", "Auxiliar", False),
]

PADRES = [
    (1, "Administrativos", 1),
    (2, "Académicos", 2),
    (3, "Extras", 3),
]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _leer_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def seed_catalogo(db) -> dict[str, int]:
    """3 sectores + 4 grupos + 53 areas desde mapeo-areas-dedup.csv.

    Idempotente por nombre. Se crea completo: los grupos citan a los sectores, asi que
    quien lo llame no tiene que acordarse de insertarlos antes.
    """
    filas = _leer_csv(CATALOGO_CSV)
    padres = {nombre: pid for pid, nombre, _ in PADRES}
    # los modelos no declaran relationship(), asi que el unit of work no puede ordenar
    # los INSERT por si solo: hay que meter los padres antes que los grupos que los citan
    db.flush()
    stats = {"padres": 0, "grupos": 0, "areas": 0}

    for pid, nombre, orden in PADRES:
        if db.get(GrupoPadre, pid) is None:
            db.add(
                GrupoPadre(id=pid, nombre=nombre, codigo=slugify(nombre), orden=orden)
            )
            stats["padres"] += 1
    db.flush()

    codigos_grupo = {g.codigo for g in db.scalars(select(Grupo)).all()}
    for padre_nombre, grupo_nombre in dict.fromkeys(
        (f["grupo_padre"].strip(), f["grupo"].strip()) for f in filas
    ):
        if not grupo_nombre:
            continue
        pid = padres[padre_nombre]
        existe = db.scalars(
            select(Grupo).where(
                Grupo.nombre == grupo_nombre, Grupo.grupo_padre_id == pid
            )
        ).first()
        if existe is None:
            codigo = codigo_unico(slugify(grupo_nombre), codigos_grupo)
            codigos_grupo.add(codigo)
            db.add(
                Grupo(
                    nombre=grupo_nombre,
                    codigo=codigo,
                    grupo_padre_id=pid,
                    activo=True,
                )
            )
            stats["grupos"] += 1
    db.flush()

    gids = {(g.grupo_padre_id, g.nombre): g.id for g in db.scalars(select(Grupo)).all()}
    codigos_area = {a.codigo for a in db.scalars(select(Area)).all()}
    for f in filas:
        pid = padres[f["grupo_padre"].strip()]
        nombre = f["nombre"].strip()
        existe = db.scalars(
            select(Area).where(Area.nombre == nombre, Area.grupo_padre_id == pid)
        ).first()
        if existe is not None:
            continue
        grupo_nombre = f["grupo"].strip()
        codigo = codigo_unico(slugify(nombre), codigos_area)
        codigos_area.add(codigo)
        db.add(
            Area(
                nombre=nombre,
                codigo=codigo,
                grupo_padre_id=pid,
                grupo_id=gids.get((pid, grupo_nombre)) if grupo_nombre else None,
                activo=f["activo"].strip() == "1",
            )
        )
        stats["areas"] += 1
    db.flush()
    return stats


def seed_atenciones(db) -> dict[str, int]:
    """Carga el CSV de atenciones. Deriva los 3 FK desde el area, no se teclea jerarquia.

    Idempotente por created_at (con microsegundos alcanza como clave natural): se puede
    re-extraer el CSV de prod y volver a correrlo para traer lo nuevo sin duplicar.

    Si un area, tecnico o colaborador no existe, falla ruidosamente: una fila con
    jerarquia NULL o colaborador NULL es exactamente el bug que estamos cerrando.
    """
    filas = _leer_csv(ATENCIONES_CSV)
    ya = set(db.scalars(select(Atencion.created_at)).all())
    usuarios = {u.email: u.id for u in db.scalars(select(Usuario)).all()}
    areas = {a.nombre: a for a in db.scalars(select(Area)).all()}
    stats = {"atenciones": 0, "con_colaborador": 0, "fuera_de_turno": 0}

    for f in filas:
        creado = datetime.fromisoformat(f["created_at"].strip())
        if creado in ya:
            continue
        area = areas.get(f["area"].strip())
        if area is None:
            raise RuntimeError(f"Area '{f['area']}' no existe en el catalogo")
        email = f["tecnico_email"].strip()
        if email not in usuarios:
            raise RuntimeError(f"Tecnico '{email}' no existe en Usuarios")
        colab_email = f["colaborador_email"].strip()
        if colab_email and colab_email not in usuarios:
            raise RuntimeError(f"Colaborador '{colab_email}' no existe en Usuarios")
        fuera = f["fuera_de_turno"].strip() == "true"
        db.add(
            Atencion(
                usuario_id=usuarios[email],
                grupo_padre_id=area.grupo_padre_id,
                grupo_id=area.grupo_id,
                area_id=area.id,
                area_solicitante=area.nombre,
                medio_solicitud=f["medio_solicitud"].strip(),
                usuario_solicitante=f["usuario_solicitante"].strip(),
                categoria=f["categoria"].strip(),
                descripcion=f["descripcion"],
                solucion=f["solucion"],
                observaciones=f["observaciones"] or None,
                enlace_apoyo=f["enlace_apoyo"] or None,
                colaborador_id=usuarios[colab_email] if colab_email else None,
                fuera_de_turno=fuera,
                fecha_registro=date.fromisoformat(f["fecha_registro"].strip()),
                created_at=creado,
            )
        )
        stats["atenciones"] += 1
        stats["con_colaborador"] += 1 if colab_email else 0
        stats["fuera_de_turno"] += 1 if fuera else 0
    db.flush()
    return stats


def run_seed() -> dict[str, int]:
    password = os.getenv("SEED_PASSWORD")
    if not password:
        raise RuntimeError("Falta SEED_PASSWORD")
    now = datetime.now(UTC)
    hashed = hash_password(password)
    stats = {"usuarios_insertados": 0, "usuarios_actualizados": 0}
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
        stats |= seed_catalogo(db)
        stats |= seed_atenciones(db)
        db.commit()
    return stats


if __name__ == "__main__":
    print(run_seed())
