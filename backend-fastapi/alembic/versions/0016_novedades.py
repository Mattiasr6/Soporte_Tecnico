"""Novedades: muro de turno para auxiliares (Fase 1).

Revision ID: 0016_novedades
Revises: 0015_lab_medio
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_novedades"
down_revision: str | None = "0015_lab_medio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "Novedades",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("UsuarioId", sa.Integer(), nullable=False),
        sa.Column("AuxiliarNombre", sa.String(255), nullable=False),
        sa.Column("Tipo", sa.String(20), nullable=False),
        sa.Column("Descripcion", sa.String(2000), nullable=False),
        sa.Column("Turno", sa.String(20), nullable=True),
        sa.Column("LaboratorioId", sa.Integer(), nullable=True),
        sa.Column("FotoPath", sa.String(500), nullable=True),
        sa.Column("Estado", sa.String(20), nullable=False),
        sa.Column("FechaRegistro", sa.Date(), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["UsuarioId"], ["Usuarios.Id"]),
        sa.ForeignKeyConstraint(["LaboratorioId"], ["Laboratorios.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_Novedades_Tipo", "Novedades", ["Tipo"])
    op.create_index("IX_Novedades_UsuarioId", "Novedades", ["UsuarioId"])
    op.create_index("IX_Novedades_Estado", "Novedades", ["Estado"])
    op.create_index("IX_Novedades_FechaRegistro", "Novedades", ["FechaRegistro"])


def downgrade() -> None:
    op.drop_index("IX_Novedades_FechaRegistro", table_name="Novedades")
    op.drop_index("IX_Novedades_Estado", table_name="Novedades")
    op.drop_index("IX_Novedades_UsuarioId", table_name="Novedades")
    op.drop_index("IX_Novedades_Tipo", table_name="Novedades")
    op.drop_table("Novedades")
