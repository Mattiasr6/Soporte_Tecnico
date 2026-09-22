"""codigo estable para el catalogo de jerarquia

Revision ID: 0003_codigo_catalogo
Revises: de1d87cc0b82
Create Date: 2026-09-22

"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_codigo_catalogo"
down_revision: str | None = "de1d87cc0b82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = ("GruposPadres", "Grupos", "Areas")


def _slug(texto: str) -> str:
    """Duplicado a proposito de app/services/slugs.py: una migracion no debe
    depender de codigo de la app, que sigue evolucionando."""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in s if not unicodedata.combining(c))
    limpio = "".join(c if c.isalnum() else "-" for c in s.lower())
    return "-".join(p for p in limpio.split("-") if p)[:60]


def _agregar_codigo(tabla: str) -> None:
    op.add_column(tabla, sa.Column("Codigo", sa.String(60), nullable=True))
    conexion = op.get_bind()
    filas = conexion.execute(
        sa.text(f'SELECT "Id", "Nombre" FROM "{tabla}" ORDER BY "Id"')
    ).fetchall()
    usados: set[str] = set()
    for id_, nombre in filas:
        base = _slug(nombre) or f"nodo-{id_}"
        codigo, n = base, 2
        while codigo in usados:
            codigo, n = f"{base}-{n}", n + 1
        usados.add(codigo)
        conexion.execute(
            sa.text(f'UPDATE "{tabla}" SET "Codigo" = :codigo WHERE "Id" = :id'),
            {"codigo": codigo, "id": id_},
        )
    op.alter_column(tabla, "Codigo", existing_type=sa.String(60), nullable=False)
    op.create_unique_constraint(f"uq_{tabla}_Codigo", tabla, ["Codigo"])


def upgrade() -> None:
    for tabla in TABLAS:
        _agregar_codigo(tabla)


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_constraint(f"uq_{tabla}_Codigo", tabla, type_="unique")
        op.drop_column(tabla, "Codigo")
