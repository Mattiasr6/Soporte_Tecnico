"""laboratorios service foundation: Laboratorios, LabCategorias, LabAtenciones.

Revision ID: 0011_laboratorios
Revises: 0010_sugerencias
Create Date: 2026-10-01
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0011_laboratorios"
down_revision: str | None = "0010_sugerencias"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LABORATORIOS = [(f"LAB-{i:02d}", f"TBD-{i:02d}") for i in range(1, 11)]
CATEGORIAS = (
    "Mantenimiento preventivo",
    "Mantenimiento correctivo",
    "Calibración",
    "Otros",
)


def upgrade() -> None:
    op.create_table(
        "Laboratorios",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("Codigo", sa.String(20), unique=True, nullable=False),
        sa.Column("Nombre", sa.String(200), nullable=False),
        sa.Column("Activa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "LabCategorias",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("Nombre", sa.String(200), unique=True, nullable=False),
        sa.Column("Activa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "LabAtenciones",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column(
            "UsuarioId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=False
        ),
        sa.Column(
            "LaboratorioId",
            sa.Integer(),
            sa.ForeignKey("Laboratorios.Id"),
            nullable=False,
        ),
        sa.Column(
            "CategoriaId",
            sa.Integer(),
            sa.ForeignKey("LabCategorias.Id"),
            nullable=False,
        ),
        sa.Column("AuxiliarNombre", sa.String(255), nullable=False),
        sa.Column("Descripcion", sa.String(1000), nullable=False),
        sa.Column("Solucion", sa.String(1000), nullable=False),
        sa.Column("Observaciones", sa.String(2000), nullable=True),
        sa.Column(
            "FueraDeTurno", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("FechaRegistro", sa.Date(), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "IX_LabAtenciones_LaboratorioId", "LabAtenciones", ["LaboratorioId"]
    )
    op.create_index("IX_LabAtenciones_CategoriaId", "LabAtenciones", ["CategoriaId"])
    op.create_index("IX_LabAtenciones_UsuarioId", "LabAtenciones", ["UsuarioId"])
    op.create_index(
        "IX_LabAtenciones_FechaRegistro", "LabAtenciones", ["FechaRegistro"]
    )

    ahora = datetime.now(UTC)
    op.bulk_insert(
        sa.table(
            "Laboratorios",
            sa.column("Codigo", sa.String(20)),
            sa.column("Nombre", sa.String(200)),
            sa.column("Activa", sa.Boolean()),
            sa.column("CreatedAt", sa.DateTime(timezone=True)),
        ),
        [
            {
                "Codigo": codigo,
                "Nombre": nombre,
                "Activa": True,
                "CreatedAt": ahora,
            }
            for codigo, nombre in LABORATORIOS
        ],
    )
    op.bulk_insert(
        sa.table(
            "LabCategorias",
            sa.column("Nombre", sa.String(200)),
            sa.column("Activa", sa.Boolean()),
            sa.column("CreatedAt", sa.DateTime(timezone=True)),
        ),
        [
            {"Nombre": nombre, "Activa": True, "CreatedAt": ahora}
            for nombre in CATEGORIAS
        ],
    )


def downgrade() -> None:
    op.drop_index("IX_LabAtenciones_FechaRegistro", table_name="LabAtenciones")
    op.drop_index("IX_LabAtenciones_UsuarioId", table_name="LabAtenciones")
    op.drop_index("IX_LabAtenciones_CategoriaId", table_name="LabAtenciones")
    op.drop_index("IX_LabAtenciones_LaboratorioId", table_name="LabAtenciones")
    op.drop_table("LabAtenciones")
    op.drop_table("LabCategorias")
    op.drop_table("Laboratorios")
