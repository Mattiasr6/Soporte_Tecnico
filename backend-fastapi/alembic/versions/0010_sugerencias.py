"""buzón de sugerencias: cualquier usuario propone, Jefe cambia estado

Revision ID: 0010_sugerencias
Revises: 0009_ia_observabilidad
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_sugerencias"
down_revision: str | None = "0009_ia_observabilidad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "Sugerencias",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("UsuarioId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=False),
        sa.Column("Texto", sa.String(1000), nullable=False),
        sa.Column("Estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("Sugerencias")
