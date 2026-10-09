"""Schema `horarios`: Saturday planner (several auxiliares per turno, hours per date).

Ported from Django `auxiliares/horarios-sabados/`: a month of Saturdays where
each date has its own start/end hours per turno and several auxiliares per
turno, and a date can be cleared.

- `sabados`: one planned Saturday (date + optional note). Deleting it clears
  the date (its assignments and hour overrides cascade).
- `sabado_horarios`: optional hours of one turno on one date; without a row the
  turno uses `horarios_turno`.
- `rotacion_sabados` becomes the assignment table: one row per date and
  auxiliar (an auxiliar works one turno per Saturday), both NOT NULL. The
  per-row note moves to `sabados.nota`; deleting a perfil drops its rows.

Data migration: every existing row creates its `sabados` date with the row's
note. A row without turno cannot be an assignment, so the auxiliar's name is
appended to the date note ("Sin turno: <nombre>") and the row is removed;
rows without auxiliar are removed too (their date and note stay).

Downgrade keeps the first assignment of each date (lowest id) with the date
note, adds a bare row for a planned date without assignments, and drops the
hour overrides: the old table only held one auxiliar per date.

Revision ID: 0026_horarios_sabados_plan
Revises: 0025_horarios_novedades_cierre
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026_horarios_sabados_plan"
down_revision: str | None = "0025_horarios_novedades_cierre"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
CREATE TABLE horarios.sabados (
    fecha date PRIMARY KEY,
    nota text,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT sabados_nota_check CHECK (((nota IS NULL) OR (char_length(nota) <= 200)))
);

CREATE TABLE horarios.sabado_horarios (
    fecha date NOT NULL REFERENCES horarios.sabados(fecha) ON DELETE CASCADE,
    turno text NOT NULL,
    hora_inicio time without time zone NOT NULL,
    hora_fin time without time zone NOT NULL,
    PRIMARY KEY (fecha, turno),
    CONSTRAINT sabado_horarios_turno_check
      CHECK ((turno = ANY (ARRAY['M'::text, 'MD'::text, 'T'::text, 'N'::text]))),
    CONSTRAINT sabado_horarios_rango CHECK ((hora_fin > hora_inicio))
);

-- Existing rows: fecha was unique, so each one becomes its own date.
INSERT INTO horarios.sabados (fecha, nota, creado_en, actualizado_en)
SELECT r.fecha, r.nota, r.creado_en, r.creado_en
  FROM horarios.rotacion_sabados r;

UPDATE horarios.sabados s
   SET nota = left(concat_ws(' · ', s.nota, 'Sin turno: ' || p.nombre_completo), 200)
  FROM horarios.rotacion_sabados r
  JOIN horarios.perfiles p ON p.id = r.auxiliar_id
 WHERE r.fecha = s.fecha AND r.turno IS NULL;

DELETE FROM horarios.rotacion_sabados WHERE auxiliar_id IS NULL OR turno IS NULL;

ALTER TABLE horarios.rotacion_sabados
  DROP CONSTRAINT rotacion_sabados_fecha_key,
  DROP CONSTRAINT rotacion_sabados_textos_check,
  DROP CONSTRAINT rotacion_sabados_auxiliar_id_fkey,
  DROP COLUMN nota,
  ALTER COLUMN auxiliar_id SET NOT NULL,
  ALTER COLUMN turno SET NOT NULL,
  ADD CONSTRAINT rotacion_sabados_auxiliar_id_fkey FOREIGN KEY (auxiliar_id)
      REFERENCES horarios.perfiles(id) ON DELETE CASCADE,
  ADD CONSTRAINT rotacion_sabados_fecha_fkey FOREIGN KEY (fecha)
      REFERENCES horarios.sabados(fecha) ON DELETE CASCADE,
  ADD CONSTRAINT rotacion_sabados_fecha_auxiliar_key UNIQUE (fecha, auxiliar_id);
"""

DOWNGRADE = r"""
ALTER TABLE horarios.rotacion_sabados
  DROP CONSTRAINT rotacion_sabados_fecha_auxiliar_key,
  DROP CONSTRAINT rotacion_sabados_fecha_fkey,
  DROP CONSTRAINT rotacion_sabados_auxiliar_id_fkey,
  ALTER COLUMN auxiliar_id DROP NOT NULL,
  ALTER COLUMN turno DROP NOT NULL,
  ADD COLUMN nota text,
  ADD CONSTRAINT rotacion_sabados_textos_check
      CHECK (((nota IS NULL) OR (char_length(nota) <= 200))),
  ADD CONSTRAINT rotacion_sabados_auxiliar_id_fkey FOREIGN KEY (auxiliar_id)
      REFERENCES horarios.perfiles(id) ON DELETE SET NULL;

DELETE FROM horarios.rotacion_sabados r
 USING horarios.rotacion_sabados o
 WHERE o.fecha = r.fecha AND o.id < r.id;

UPDATE horarios.rotacion_sabados r
   SET nota = s.nota
  FROM horarios.sabados s
 WHERE s.fecha = r.fecha;

INSERT INTO horarios.rotacion_sabados (fecha, nota, creado_en)
SELECT s.fecha, s.nota, s.creado_en
  FROM horarios.sabados s
 WHERE NOT EXISTS (SELECT 1 FROM horarios.rotacion_sabados r WHERE r.fecha = s.fecha);

ALTER TABLE horarios.rotacion_sabados
  ADD CONSTRAINT rotacion_sabados_fecha_key UNIQUE (fecha);

DROP TABLE horarios.sabado_horarios;
DROP TABLE horarios.sabados;
"""


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
