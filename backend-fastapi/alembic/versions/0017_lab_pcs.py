"""PCs por laboratorio: dibujo (fila/col) como wireframe de sala de cine.

Revision ID: 0017_lab_pcs
Revises: 0016_novedades
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_lab_pcs"
down_revision: str | None = "0016_novedades"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "LabPcs",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("LaboratorioId", sa.Integer(), nullable=False),
        sa.Column("Nombre", sa.String(50), nullable=False),
        sa.Column("Fila", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("Col", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("Activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["LaboratorioId"], ["Laboratorios.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_LabPcs_LaboratorioId", "LabPcs", ["LaboratorioId"])
    op.create_index(
        "IX_LabPcs_LaboratorioId_Pos", "LabPcs", ["LaboratorioId", "Fila", "Col"]
    )
    op.add_column(
        "Laboratorios",
        sa.Column("FilasPc", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "Laboratorios",
        sa.Column("ColsPc", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("Laboratorios", "ColsPc")
    op.drop_column("Laboratorios", "FilasPc")
    op.drop_index("IX_LabPcs_LaboratorioId_Pos", table_name="LabPcs")
    op.drop_index("IX_LabPcs_LaboratorioId", table_name="LabPcs")
    op.drop_table("LabPcs")
