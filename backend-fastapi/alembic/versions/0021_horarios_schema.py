"""Schema `horarios`: the ASIGNACION data model ported from Supabase.

Loads the versioned SQL files in alembic/sql/0021_horarios (in name order):
prelude (schema + fn_usuario_actual), the ported tables/functions/triggers,
the perfiles <-> Usuarios link and the catalog seed. 99_rls_reference.sql is
documentation only and is not executed.

Revision ID: 0021_horarios_schema
Revises: 0020_novedad_entregado
Create Date: 2026-10-08
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0021_horarios_schema"
down_revision: str | None = "0020_novedad_entregado"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "0021_horarios"
SQL_FILES = (
    "01_prelude.sql",
    "02_schema.sql",
    "03_perfiles_link.sql",
    "04_seed.sql",
)


def _run_sql(sql: str) -> None:
    # Straight to the psycopg cursor (same connection and transaction as
    # Alembic): no parameters means no placeholder parsing, so "%" in format()
    # strings and ":" in time literals are left alone, and psycopg accepts the
    # multi-statement script as is.
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    # Function bodies reference objects created later in the same script.
    _run_sql("SET LOCAL check_function_bodies = off")
    for name in SQL_FILES:
        _run_sql((SQL_DIR / name).read_text(encoding="utf-8"))
    _run_sql("SET LOCAL check_function_bodies = on")


def downgrade() -> None:
    _run_sql("DROP SCHEMA horarios CASCADE")
