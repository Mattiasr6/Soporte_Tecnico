"""A quién se devolvió el objeto (Novedades.EntregadoA).

Revision ID: 0020_novedad_entregado
Revises: 0019_auditoria
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_novedad_entregado"
down_revision: str | None = "0019_auditoria"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "Novedades", sa.Column("EntregadoA", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("Novedades", "EntregadoA")
