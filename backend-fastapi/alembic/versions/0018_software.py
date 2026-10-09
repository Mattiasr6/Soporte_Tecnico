"""Seguimiento de programas: catalogo Software, SoftwareLab, PcSoftware,
plantillas, PcNombre en atenciones y ficha tecnica en laboratorios.

Revision ID: 0018_software
Revises: 0017_lab_pcs
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_software"
down_revision: str | None = "0017_lab_pcs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "Software",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("Nombre", sa.String(200), nullable=False),
        sa.Column("Licencia", sa.String(50), nullable=False, server_default="gratuita"),
        sa.Column("Uso", sa.String(500), nullable=False, server_default=""),
        sa.Column("Esencial", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("Docentes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("Activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_Software_Nombre", "Software", ["Nombre"])
    op.create_table(
        "SoftwareLab",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("SoftwareId", sa.Integer(), nullable=False),
        sa.Column("LaboratorioId", sa.Integer(), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["SoftwareId"], ["Software.Id"]),
        sa.ForeignKeyConstraint(["LaboratorioId"], ["Laboratorios.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_SoftwareLab_SoftwareId", "SoftwareLab", ["SoftwareId"])
    op.create_index("IX_SoftwareLab_LaboratorioId", "SoftwareLab", ["LaboratorioId"])
    op.create_table(
        "PcSoftware",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("PcId", sa.Integer(), nullable=False),
        sa.Column("SoftwareId", sa.Integer(), nullable=False),
        sa.Column("Estado", sa.String(20), nullable=False, server_default="instalado"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("UpdatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["PcId"], ["LabPcs.Id"]),
        sa.ForeignKeyConstraint(["SoftwareId"], ["Software.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_PcSoftware_PcId", "PcSoftware", ["PcId"])
    op.create_index("IX_PcSoftware_SoftwareId", "PcSoftware", ["SoftwareId"])
    op.create_table(
        "LabPlantillas",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("Nombre", sa.String(100), nullable=False),
        sa.Column("Categoria", sa.String(200), nullable=False, server_default="SOFTWARE"),
        sa.Column("Descripcion", sa.String(2000), nullable=False, server_default=""),
        sa.Column("Solucion", sa.String(2000), nullable=False, server_default=""),
        sa.Column("Turno", sa.String(20), nullable=True),
        sa.Column("Activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_LabPlantillas_Nombre", "LabPlantillas", ["Nombre"])
    op.add_column(
        "LabAtenciones", sa.Column("PcNombre", sa.String(50), nullable=True)
    )
    op.add_column(
        "Laboratorios", sa.Column("Procesador", sa.String(200), nullable=True)
    )
    op.add_column("Laboratorios", sa.Column("Ram", sa.String(100), nullable=True))
    op.add_column("Laboratorios", sa.Column("Disco", sa.String(100), nullable=True))
    op.add_column("Laboratorios", sa.Column("Marca", sa.String(100), nullable=True))
    op.add_column("Laboratorios", sa.Column("Gpu", sa.String(100), nullable=True))
    op.add_column(
        "Laboratorios", sa.Column("Monitores", sa.String(100), nullable=True)
    )
    op.add_column("Laboratorios", sa.Column("Sillas", sa.Integer(), nullable=True))
    op.add_column("Laboratorios", sa.Column("Capacidad", sa.Integer(), nullable=True))
    op.add_column(
        "Laboratorios", sa.Column("PcsEstudiantes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "Laboratorios", sa.Column("PcsDocentes", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("Laboratorios", "PcsDocentes")
    op.drop_column("Laboratorios", "PcsEstudiantes")
    op.drop_column("Laboratorios", "Capacidad")
    op.drop_column("Laboratorios", "Sillas")
    op.drop_column("Laboratorios", "Monitores")
    op.drop_column("Laboratorios", "Gpu")
    op.drop_column("Laboratorios", "Marca")
    op.drop_column("Laboratorios", "Disco")
    op.drop_column("Laboratorios", "Ram")
    op.drop_column("Laboratorios", "Procesador")
    op.drop_column("LabAtenciones", "PcNombre")
    op.drop_index("IX_LabPlantillas_Nombre", table_name="LabPlantillas")
    op.drop_table("LabPlantillas")
    op.drop_index("IX_PcSoftware_SoftwareId", table_name="PcSoftware")
    op.drop_index("IX_PcSoftware_PcId", table_name="PcSoftware")
    op.drop_table("PcSoftware")
    op.drop_index("IX_SoftwareLab_LaboratorioId", table_name="SoftwareLab")
    op.drop_index("IX_SoftwareLab_SoftwareId", table_name="SoftwareLab")
    op.drop_table("SoftwareLab")
    op.drop_index("IX_Software_Nombre", table_name="Software")
    op.drop_table("Software")
