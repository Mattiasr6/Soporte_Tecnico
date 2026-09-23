"""Levanta la base de produccion de la v2 desde cero.

Uso desde backend-fastapi/ (con el .env cargado):
    python scripts/promover_a_produccion.py <DATABASE_URL_destino>

Deja: el catalogo, los usuarios de v1 con su contrasena, las atenciones de septiembre
y los horarios que ya estan cargados en la base de origen (el DATABASE_URL del .env).

Por que los usuarios salen de v1 y no del seed: los hashes de prod son bcrypt ($2b$) y
v2 usa el mismo algoritmo, asi que se copian tal cual y nadie tiene que cambiar su
contrasena. El seed los dejaria a todos con la misma.

El destino tiene que tener el esquema puesto (alembic upgrade head) y estar vacio: si
ya tiene usuarios o atenciones, el script se niega a seguir.
"""

import csv
import os
import subprocess
import sys
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.area import Area
from app.models.atencion import Atencion
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre
from app.models.horario import Horario
from app.models.usuario import Usuario
from scripts.seed import seed_atenciones, seed_catalogo

CONTENEDOR = "soporte-postgres"

SQL_USUARIOS = """
COPY (
    SELECT "Email", "PasswordHash", "DisplayName", "Notas", "Especialidad",
           "Role", "EstadoActual", "CanViewDashboard", "CreatedAt", "UpdatedAt"
    FROM "Usuarios" ORDER BY "Id"
) TO STDOUT WITH (FORMAT csv, HEADER true, NULL '')
"""


def usuarios_de_v1() -> list[dict[str, str]]:
    salida = subprocess.run(
        ["docker", "exec", CONTENEDOR, "psql", "-U", "soporte", "-d", "soporte", "-c", SQL_USUARIOS],
        capture_output=True,
        check=True,
    )
    return list(csv.DictReader(salida.stdout.decode("utf-8").splitlines()))


def _texto(valor: str) -> str | None:
    return valor.strip() or None


def copiar_usuarios(db: Session, filas: list[dict[str, str]]) -> int:
    for f in filas:
        db.add(
            Usuario(
                email=f["Email"].strip(),
                password_hash=_texto(f["PasswordHash"]),
                display_name=f["DisplayName"].strip(),
                notas=_texto(f["Notas"]),
                especialidad=_texto(f["Especialidad"]),
                role=f["Role"].strip(),
                estado_actual=f["EstadoActual"].strip(),
                can_view_dashboard=f["CanViewDashboard"].strip() == "t",
                created_at=datetime.fromisoformat(f["CreatedAt"].strip()),
                updated_at=datetime.fromisoformat(f["UpdatedAt"].strip()),
            )
        )
    db.flush()
    return len(filas)


def copiar_horarios(db: Session, origen: Session) -> int:
    emails = {u.id: u.email for u in origen.scalars(select(Usuario)).all()}
    destinos = {u.email: u.id for u in db.scalars(select(Usuario)).all()}
    filas = origen.scalars(select(Horario)).all()
    copiados = 0
    for h in filas:
        email = emails.get(h.usuario_id)
        destino_id = destinos.get(email) if email else None
        if destino_id is None:
            continue
        db.add(
            Horario(
                usuario_id=destino_id,
                label=h.label,
                hora_inicio1=h.hora_inicio1,
                hora_fin1=h.hora_fin1,
                hora_inicio2=h.hora_inicio2,
                hora_fin2=h.hora_fin2,
                dia_semana=h.dia_semana,
                mes=h.mes,
                anio=h.anio,
                created_at=h.created_at,
            )
        )
        copiados += 1
    db.flush()
    return copiados


def _contar(db: Session, modelo: Any) -> int:
    return len(db.scalars(select(modelo)).all())


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: python scripts/promover_a_produccion.py <DATABASE_URL_destino>")
        return 2
    destino_url = sys.argv[1]
    origen_url = os.environ.get("DATABASE_URL")
    if not origen_url:
        print("falta DATABASE_URL (la base de origen, de donde salen los horarios)")
        return 2

    motor = create_engine(destino_url)
    Fabrica = sessionmaker(bind=motor)
    with Fabrica() as destino:
        try:
            destino.execute(select(Usuario).limit(1))
        except SQLAlchemyError as e:
            print(f"el destino no tiene el esquema: corre alembic upgrade head antes\n  {e}")
            return 2
        usuarios_ya = _contar(destino, Usuario)
        atenciones_ya = _contar(destino, Atencion)
        if usuarios_ya or atenciones_ya:
            print(f"el destino no esta vacio: {usuarios_ya} usuarios y {atenciones_ya} atenciones")
            return 2

        print("copiando usuarios de v1 (con su hash bcrypt)...")
        copiados = copiar_usuarios(destino, usuarios_de_v1())
        sin_hash = destino.scalars(
            select(Usuario).where(Usuario.password_hash.is_(None))
        ).all()
        print(f"  usuarios: {copiados}")
        for u in sin_hash:
            print(f"  AVISO: {u.email} viene sin hash, no va a poder entrar")

        print("cargando catalogo...")
        stats_catalogo = seed_catalogo(destino)

        print("cargando atenciones de septiembre...")
        stats_atenciones = seed_atenciones(destino)

        print("copiando horarios del origen...")
        with sessionmaker(bind=create_engine(origen_url))() as origen:
            horarios = copiar_horarios(destino, origen)

        destino.commit()

        print("\n=== destino ===")
        print(f"  sectores  : {_contar(destino, GrupoPadre)}")
        print(f"  grupos    : {_contar(destino, Grupo)}  (nuevos: {stats_catalogo['grupos']})")
        print(f"  areas     : {_contar(destino, Area)}  (nuevas: {stats_catalogo['areas']})")
        print(f"  usuarios  : {_contar(destino, Usuario)}")
        print(f"  atenciones: {_contar(destino, Atencion)}  (nuevas: {stats_atenciones['atenciones']})")
        print(f"  horarios  : {_contar(destino, Horario)}  (copiados: {horarios})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
