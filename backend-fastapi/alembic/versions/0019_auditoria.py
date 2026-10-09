"""Rastro de cambios esenciales: solo un Jefe puede leerlo.

Revision ID: 0019_auditoria
Revises: 0018_software
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_auditoria"
down_revision: str | None = "0018_software"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "AuditoriaCambios",
        sa.Column("Id", sa.Integer(), nullable=False),
        sa.Column("Fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("UsuarioId", sa.Integer(), nullable=True),
        sa.Column("UsuarioEmail", sa.String(200), nullable=False, server_default=""),
        sa.Column("UsuarioNombre", sa.String(200), nullable=False, server_default=""),
        sa.Column("Rol", sa.String(50), nullable=False, server_default=""),
        sa.Column("Accion", sa.String(50), nullable=False),
        sa.Column("Entidad", sa.String(50), nullable=False),
        sa.Column("EntidadId", sa.Integer(), nullable=True),
        sa.Column("Detalle", sa.Text(), nullable=False, server_default=""),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["UsuarioId"], ["Usuarios.Id"]),
        sa.PrimaryKeyConstraint("Id"),
    )
    op.create_index("IX_AuditoriaCambios_UsuarioId", "AuditoriaCambios", ["UsuarioId"])
    op.create_index("IX_AuditoriaCambios_Entidad", "AuditoriaCambios", ["Entidad"])
    op.create_index(
        "IX_AuditoriaCambios_Fecha", "AuditoriaCambios", ["Fecha"], unique=False
    )


def downgrade() -> None:
    op.drop_index("IX_AuditoriaCambios_Fecha", table_name="AuditoriaCambios")
    op.drop_index("IX_AuditoriaCambios_Entidad", table_name="AuditoriaCambios")
    op.drop_index("IX_AuditoriaCambios_UsuarioId", table_name="AuditoriaCambios")
    op.drop_table("AuditoriaCambios")
