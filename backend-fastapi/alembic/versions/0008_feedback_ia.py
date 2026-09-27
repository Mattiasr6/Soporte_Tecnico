"""feedback de Wilmercito: calificar respuestas para promover a KB (loop de aprendizaje)

Revision ID: 0008_feedback_ia
Revises: 0007_token_version
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_feedback_ia"
down_revision: str | None = "0007_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "FeedbackIA",
        sa.Column("Id", sa.Integer(), primary_key=True),
        sa.Column("UsuarioId", sa.Integer(), sa.ForeignKey("Usuarios.Id"), nullable=False),
        sa.Column("Pregunta", sa.String(500), nullable=False),
        sa.Column("Respuesta", sa.String(2000), nullable=False),
        sa.Column("Fuente", sa.String(100), nullable=True),
        sa.Column("Puntaje", sa.Integer(), nullable=False),
        sa.Column("Promovido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("FeedbackIA")
