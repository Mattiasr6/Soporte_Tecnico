"""Schema `horarios`: save a class even when its laboratorio is busy some days.

Ports upstream ASIGNACION script 34 (d0d7ad1): rpc_guardar_asignacion accepts
p.reubicaciones and moves those days to another ambiente or an aula in the same
operation. SQL lives in alembic/sql/0022_horarios; the downgrade restores the
0021 definition of the function (saved reubicaciones rows are kept).

Revision ID: 0022_horarios_reubica_choques
Revises: 0021_horarios_schema
Create Date: 2026-10-09
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0022_horarios_reubica_choques"
down_revision: str | None = "0021_horarios_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql" / "0022_horarios"


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql((SQL_DIR / "01_rpc_guardar_asignacion.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    _run_sql(
        (SQL_DIR / "down_01_rpc_guardar_asignacion.sql").read_text(encoding="utf-8")
    )
