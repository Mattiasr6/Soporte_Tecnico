"""add Turno to LabAtenciones (nullable, indexed).

Revision ID: 0014_lab_turno
Revises: 0013_soporte_lab
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_lab_turno"
down_revision: str | None = "0013_soporte_lab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("LabAtenciones", sa.Column("Turno", sa.String(20), nullable=True))
    op.create_index("IX_LabAtenciones_Turno", "LabAtenciones", ["Turno"])


def downgrade() -> None:
    op.drop_index("IX_LabAtenciones_Turno", table_name="LabAtenciones")
    op.drop_column("LabAtenciones", "Turno")
