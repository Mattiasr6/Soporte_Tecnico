"""version de token: cambiar la contrasena invalida las sesiones abiertas

Revision ID: 0007_token_version
Revises: 0006_usuarios_secuencia
Create Date: 2026-09-24

El JWT no depende del hash, asi que hasta ahora una sesion iniciada antes del cambio
seguia valida. Con este contador, el token lleva la version que tenia el usuario al
emitirse y require_user rechaza lo que no coincida. Un timestamp no servia: el claim
iat tiene precision de segundos, asi que un token emitido en el mismo segundo del
cambio sobrevivia.

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_token_version"
down_revision: str | None = "0006_usuarios_secuencia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "Usuarios",
        sa.Column(
            "TokenVersion", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )


def downgrade() -> None:
    op.drop_column("Usuarios", "TokenVersion")
