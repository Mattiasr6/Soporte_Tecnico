"""add SOPORTE lab as 11th card (idempotent).

Revision ID: 0013_soporte_lab
Revises: 0012_lab_categorias_reales
Create Date: 2026-10-01
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import text

from alembic import op

revision: str = "0013_soporte_lab"
down_revision: str | None = "0012_lab_categorias_reales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODIGO = "SOPORTE"
NOMBRE = "Soporte Técnico"


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text('SELECT "Id" FROM "Laboratorios" WHERE "Codigo" = :c'),
        {"c": CODIGO},
    ).first()
    if row is None:
        conn.execute(
            text(
                'INSERT INTO "Laboratorios" '
                '("Codigo", "Nombre", "Activa", "CreatedAt") '
                "VALUES (:c, :n, TRUE, :ahora)"
            ),
            {"c": CODIGO, "n": NOMBRE, "ahora": datetime.now(UTC)},
        )


def downgrade() -> None:
    op.get_bind().execute(
        text('DELETE FROM "Laboratorios" WHERE "Codigo" = :c'),
        {"c": CODIGO},
    )
