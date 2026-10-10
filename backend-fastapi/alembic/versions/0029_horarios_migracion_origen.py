"""Schema `horarios`: source-id map for the one-off Soporte → horarios data move.

`scripts/migrar_soporte_a_horarios.py` copies the old Soporte lab data
(`LabAtenciones`, the auxiliar JSON files) onto the horarios tables at cutover.
It runs after `alembic upgrade head` and may be re-run: every source row it
moved is recorded here, so a second run skips it instead of duplicating it.

- origen: source table or file (`LabAtenciones`, `horarios_sabados.json`).
- origen_id: source key as text (row id, or the ISO date of a Saturday).
- destino / destino_id: target table and key (text: bigint ids and dates).

No data is moved by this migration. Downgrade drops the map only; the
migrated horarios rows stay (they are ordinary data by then).

Revision ID: 0029_horarios_migracion_origen
Revises: 0028_horarios_ambiente_ficha
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_horarios_migracion_origen"
down_revision: str | None = "0028_horarios_ambiente_ficha"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
CREATE TABLE horarios.migracion_origen (
    origen      text        NOT NULL,
    origen_id   text        NOT NULL,
    destino     text        NOT NULL,
    destino_id  text        NOT NULL,
    migrado_en  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (origen, origen_id)
);

COMMENT ON TABLE horarios.migracion_origen IS
    'Source rows already moved by scripts/migrar_soporte_a_horarios.py (idempotency map).';
"""

DOWNGRADE = r"""
DROP TABLE IF EXISTS horarios.migracion_origen;
"""


def _run_sql(sql: str) -> None:
    # Raw DBAPI cursor: the SQL has no bind parameters to escape.
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
