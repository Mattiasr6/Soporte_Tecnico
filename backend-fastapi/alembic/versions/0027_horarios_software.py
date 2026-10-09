"""Schema `horarios`: software inventory and lab attention templates.

Ported from Django `auxiliares/software/` and the per-PC software panel of
`auxiliares/laboratorios/<id>/pcs/` (Soporte tables `Software`, `SoftwareLab`,
`PcSoftware`, `LabPlantillas`). No data is copied: the Soporte tables were empty
in prod (Software 0, LabPcs 0), so the horarios tables start empty.

- `software`: the catalogue. Same fields as Django: nombre (unique, case and
  surrounding blanks ignored), licencia gratuita/mixta/paga, uso, esencial
  (must be in every lab), docentes (used by teachers), activo.
- `ambiente_software`: which software a lab has (Django `SoftwareLab`, keyed by
  `ambientes.id`).
- `pc_software`: state of one software on one PC, keyed by `ambiente_pcs.id`
  (Django `PcSoftware` on `LabPcs`). instalado/falta/dañado; a PC without a row
  reads as "falta" (Django default). Removing a software from a lab drops the
  states of that lab's PCs (trigger), so a PC never keeps the state of software
  its lab no longer has.
- `plantillas_atencion`: prefilled lab attentions (Django `LabPlantillas`).
  Django's free "categoría" maps to the horarios attention `tipo` (as G3 did),
  limited to the tipos the attention form creates directly (correctivo and
  cambio_estado go through their RPCs); Django turnos map to M/MD/T/N.

Revision ID: 0027_horarios_software
Revises: 0026_horarios_sabados_plan
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027_horarios_software"
down_revision: str | None = "0026_horarios_sabados_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
CREATE TABLE horarios.software (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre text NOT NULL,
    licencia text DEFAULT 'gratuita'::text NOT NULL,
    uso text DEFAULT ''::text NOT NULL,
    esencial boolean DEFAULT false NOT NULL,
    docentes boolean DEFAULT false NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT software_nombre_check
      CHECK (((char_length(btrim(nombre)) >= 1) AND (char_length(nombre) <= 150))),
    CONSTRAINT software_licencia_check
      CHECK ((licencia = ANY (ARRAY['gratuita'::text, 'mixta'::text, 'paga'::text]))),
    CONSTRAINT software_uso_check CHECK ((char_length(uso) <= 250))
);
CREATE UNIQUE INDEX software_nombre_key ON horarios.software USING btree (lower(btrim(nombre)));
CREATE TRIGGER trg_software_actualizado BEFORE UPDATE ON horarios.software
  FOR EACH ROW EXECUTE FUNCTION horarios.fn_set_actualizado_en();

CREATE TABLE horarios.ambiente_software (
    ambiente_id bigint NOT NULL REFERENCES horarios.ambientes(id) ON DELETE CASCADE,
    software_id bigint NOT NULL REFERENCES horarios.software(id) ON DELETE CASCADE,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY (ambiente_id, software_id)
);
CREATE INDEX ambiente_software_software_idx ON horarios.ambiente_software USING btree (software_id);

CREATE TABLE horarios.pc_software (
    pc_id bigint NOT NULL REFERENCES horarios.ambiente_pcs(id) ON DELETE CASCADE,
    software_id bigint NOT NULL REFERENCES horarios.software(id) ON DELETE CASCADE,
    estado text NOT NULL,
    actualizado_por uuid DEFAULT horarios.fn_usuario_actual()
        REFERENCES horarios.perfiles(id) ON DELETE SET NULL,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY (pc_id, software_id),
    CONSTRAINT pc_software_estado_check
      CHECK ((estado = ANY (ARRAY['instalado'::text, 'falta'::text, 'dañado'::text])))
);
CREATE INDEX pc_software_software_idx ON horarios.pc_software USING btree (software_id);

-- A software removed from a lab takes the states of that lab's PCs with it.
CREATE FUNCTION horarios.fn_trg_ambiente_software_borrado() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'horarios'
    AS $$
begin
  delete from horarios.pc_software ps
   using horarios.ambiente_pcs pc
   where pc.id = ps.pc_id
     and pc.ambiente_id = old.ambiente_id
     and ps.software_id = old.software_id;
  return old;
end $$;
CREATE TRIGGER trg_ambiente_software_borrado AFTER DELETE ON horarios.ambiente_software
  FOR EACH ROW EXECUTE FUNCTION horarios.fn_trg_ambiente_software_borrado();

CREATE TABLE horarios.plantillas_atencion (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre text NOT NULL,
    tipo text DEFAULT 'programas'::text NOT NULL,
    descripcion text DEFAULT ''::text NOT NULL,
    solucion text DEFAULT ''::text NOT NULL,
    turno text,
    activa boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT plantillas_atencion_nombre_check
      CHECK (((char_length(btrim(nombre)) >= 1) AND (char_length(nombre) <= 100))),
    CONSTRAINT plantillas_atencion_tipo_check
      CHECK ((tipo = ANY (ARRAY['docente'::text, 'programas'::text, 'preventivo'::text, 'personal'::text]))),
    CONSTRAINT plantillas_atencion_textos_check
      CHECK (((char_length(descripcion) <= 500) AND (char_length(solucion) <= 1000))),
    CONSTRAINT plantillas_atencion_turno_check
      CHECK (((turno IS NULL) OR (turno = ANY (ARRAY['M'::text, 'MD'::text, 'T'::text, 'N'::text]))))
);
CREATE INDEX plantillas_atencion_nombre_idx ON horarios.plantillas_atencion USING btree (nombre);
CREATE TRIGGER trg_plantillas_atencion_actualizado BEFORE UPDATE ON horarios.plantillas_atencion
  FOR EACH ROW EXECUTE FUNCTION horarios.fn_set_actualizado_en();
"""

DOWNGRADE = r"""
DROP TABLE horarios.plantillas_atencion;
DROP TRIGGER trg_ambiente_software_borrado ON horarios.ambiente_software;
DROP FUNCTION horarios.fn_trg_ambiente_software_borrado();
DROP TABLE horarios.pc_software;
DROP TABLE horarios.ambiente_software;
DROP TABLE horarios.software;
"""


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
