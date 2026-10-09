"""Schema `horarios`: lab hardware sheet ("ficha del lab") on `ambientes`.

Ported from Django `auxiliares/laboratorios/<id>/pcs/` (`views_lab.py`
`FICHA_CAMPOS`, Soporte `Laboratorios` columns). The sheet is the lab's
declared standard spec, edited as one card; the real per-PC values stay in
`ambiente_pcs` (procesador, ram, almacenamiento), which may differ.

- New nullable columns with Django's sizes: procesador (<= 200), ram,
  almacenamiento (Django "disco", named like `ambiente_pcs.almacenamiento`),
  marca, gpu, monitores (<= 100), sillas, pcs_estudiantes, pcs_docentes (>= 0).
- `capacidad` already exists (NOT NULL default 0) and is reused.
- Backfill: when the Soporte `Laboratorios` table is present, its sheet values
  are copied onto the ambiente with the same codigo (blank strings ignored);
  capacidad is copied only where the ambiente still has 0.

Revision ID: 0028_horarios_ambiente_ficha
Revises: 0027_horarios_software
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_horarios_ambiente_ficha"
down_revision: str | None = "0027_horarios_software"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
ALTER TABLE horarios.ambientes
    ADD COLUMN procesador text
        CONSTRAINT ambientes_procesador_check CHECK (char_length(procesador) <= 200),
    ADD COLUMN ram text
        CONSTRAINT ambientes_ram_check CHECK (char_length(ram) <= 100),
    ADD COLUMN almacenamiento text
        CONSTRAINT ambientes_almacenamiento_check
        CHECK (char_length(almacenamiento) <= 100),
    ADD COLUMN marca text
        CONSTRAINT ambientes_marca_check CHECK (char_length(marca) <= 100),
    ADD COLUMN gpu text
        CONSTRAINT ambientes_gpu_check CHECK (char_length(gpu) <= 100),
    ADD COLUMN monitores text
        CONSTRAINT ambientes_monitores_check CHECK (char_length(monitores) <= 100),
    ADD COLUMN sillas integer
        CONSTRAINT ambientes_sillas_check CHECK (sillas >= 0),
    ADD COLUMN pcs_estudiantes integer
        CONSTRAINT ambientes_pcs_estudiantes_check CHECK (pcs_estudiantes >= 0),
    ADD COLUMN pcs_docentes integer
        CONSTRAINT ambientes_pcs_docentes_check CHECK (pcs_docentes >= 0);

COMMENT ON COLUMN horarios.ambientes.procesador IS
    'Lab sheet: standard processor (per-PC value in ambiente_pcs).';
COMMENT ON COLUMN horarios.ambientes.almacenamiento IS
    'Lab sheet: standard disk (Django "disco").';

DO $$
BEGIN
    IF to_regclass('public."Laboratorios"') IS NULL THEN
        RETURN;
    END IF;
    ALTER TABLE horarios.ambientes DISABLE TRIGGER trg_ambientes_actualizado;
    UPDATE horarios.ambientes a
       SET procesador      = left(nullif(btrim(l."Procesador"), ''), 200),
           ram             = left(nullif(btrim(l."Ram"), ''), 100),
           almacenamiento  = left(nullif(btrim(l."Disco"), ''), 100),
           marca           = left(nullif(btrim(l."Marca"), ''), 100),
           gpu             = left(nullif(btrim(l."Gpu"), ''), 100),
           monitores       = left(nullif(btrim(l."Monitores"), ''), 100),
           sillas          = CASE WHEN l."Sillas" >= 0 THEN l."Sillas" END,
           pcs_estudiantes = CASE WHEN l."PcsEstudiantes" >= 0
                                  THEN l."PcsEstudiantes" END,
           pcs_docentes    = CASE WHEN l."PcsDocentes" >= 0 THEN l."PcsDocentes" END,
           capacidad       = CASE WHEN a.capacidad = 0 AND l."Capacidad" > 0
                                  THEN l."Capacidad" ELSE a.capacidad END
      FROM public."Laboratorios" l
     WHERE upper(btrim(l."Codigo")) = upper(btrim(a.codigo));
    ALTER TABLE horarios.ambientes ENABLE TRIGGER trg_ambientes_actualizado;
END
$$;
"""

DOWNGRADE = r"""
ALTER TABLE horarios.ambientes
    DROP COLUMN procesador,
    DROP COLUMN ram,
    DROP COLUMN almacenamiento,
    DROP COLUMN marca,
    DROP COLUMN gpu,
    DROP COLUMN monitores,
    DROP COLUMN sillas,
    DROP COLUMN pcs_estudiantes,
    DROP COLUMN pcs_docentes;
"""


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
