"""add MedioSolicitud to LabAtenciones (nullable, default Presencial).

Revision ID: 0015_lab_medio
Revises: 0014_lab_turno
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_lab_medio"
down_revision: str | None = "0014_lab_turno"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "LabAtenciones",
        sa.Column(
            "MedioSolicitud", sa.String(50), nullable=True, server_default="Presencial"
        ),
    )


def downgrade() -> None:
    op.drop_column("LabAtenciones", "MedioSolicitud")
