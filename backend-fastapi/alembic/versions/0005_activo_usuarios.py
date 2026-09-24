"""baja de usuarios: columna Activo

Revision ID: 0005_activo_usuarios
Revises: 0004_horario_dia
Create Date: 2026-09-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_activo_usuarios"
down_revision: str | None = "0004_horario_dia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "Usuarios",
        sa.Column(
            "Activo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )


def downgrade() -> None:
    op.drop_column("Usuarios", "Activo")
