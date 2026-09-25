"""observabilidad IA: LogIA (huella de uso) + PropuestaIA (cola de poderes)

Revision ID: 0009_ia_observabilidad
Revises: 0008_feedback_ia
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_ia_observabilidad"
down_revision: str | None = "0008_feedback_ia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "LogIA",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("UsuarioId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=False),
        sa.Column("Pregunta", sa.String(500), nullable=False),
        sa.Column("Fuente", sa.String(100), nullable=True),
        sa.Column("Rechazado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("Ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "PropuestaIA",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("ProponenteId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=False),
        sa.Column("Tipo", sa.String(50), nullable=False),
        sa.Column("Payload", sa.Text(), nullable=False),
        sa.Column("Estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("AtencionId", sa.Integer(), sa.ForeignKey("Atenciones.Id"), nullable=True),
        sa.Column("RevisorId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=True),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("PropuestaIA")
    op.drop_table("LogIA")
