"""resincroniza la secuencia de Usuarios

Revision ID: 0006_usuarios_secuencia
Revises: 0005_activo_usuarios
Create Date: 2026-09-24

El seed inserta los 10 usuarios con Id explicito (1..10), y eso no avanza la secuencia:
quedo en 1-2 mientras el maximo real es 10. Sin este arreglo, el primer INSERT sin Id
(es decir, POST /api/usuarios) revienta con Usuarios_pkey.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_usuarios_secuencia"
down_revision: str | None = "0005_activo_usuarios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "SELECT setval("
        " pg_get_serial_sequence('\"Usuarios\"', 'Id'),"
        " GREATEST(COALESCE((SELECT MAX(\"Id\") FROM \"Usuarios\"), 1), 1)"
        ")"
    )


def downgrade() -> None:
    pass
