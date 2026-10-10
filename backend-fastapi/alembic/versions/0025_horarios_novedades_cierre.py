"""Schema `horarios`: lab novedades and shift-close (cierre) validation.

Ported from Django `novedades_vista` (Soporte table `Novedades`, tabs
"novedades" and "cierres").

Novedades get their own table instead of more columns on `reportes_turno`:
a shift report is one per auxiliar and shift close, its triggers compute the
shift hours, the delay (`minutos_retraso`) and the PCs given de baja during the
shift, its photo expires at the next noon, and its writes are tied to
fn_puede_cerrar_turno. A novedad is a free notice any operator posts at any
time, about one lab or none, shown for 3 days, so none of that applies. Mixing
both would also inflate the report counts of the dashboards. The photo reuses
the horarios photo storage (`app.services.asignacion.fotos`, folder
`novedades`).

- `novedades.turno` uses M/MD/T/N; when not given it is the turno of the
  current hour (fn_turno_horario_de, from 0024).
- `novedades.fecha` is the La Paz calendar date; the API lists the last 3 days
  (Django NOV_VIGENCIA_DIAS). Rows are kept (the day timeline still shows them).

`reportes_turno` gains `estado` (pendiente/validado/rechazado), `validado_por`
and `validado_en`. Django has no rejection note, so none is added.
fn_decidir_reporte(id, estado) validates or rejects: only
fn_puede_gestionar_auxiliares (Jefe, Encargado; Django `_gestiona_equipo`),
never on a report whose auxiliar is the requester, and only while pendiente.
Trigger trg_reportes_turno_estado sends a decided report back to pendiente when
its content (turno, novedades or a new photo) changes. Reports that already exist
when this migration runs are marked validado at migration time with no validator
(decided 2026-10-10), so the pending list starts empty in prod. The columns are
added with that default and then switched to pendiente, so no UPDATE trigger runs.

Revision ID: 0025_horarios_novedades_cierre
Revises: 0024_horarios_turno_medio
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025_horarios_novedades_cierre"
down_revision: str | None = "0024_horarios_turno_medio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
CREATE TABLE horarios.novedades (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha date DEFAULT ((now() AT TIME ZONE 'America/La_Paz'::text))::date NOT NULL,
    turno text DEFAULT horarios.fn_turno_horario_de(now()) NOT NULL,
    ambiente_id bigint REFERENCES horarios.ambientes(id) ON DELETE SET NULL,
    texto text NOT NULL,
    foto_path text,
    autor_id uuid DEFAULT horarios.fn_usuario_actual()
        REFERENCES horarios.perfiles(id) ON DELETE SET NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT novedades_turno_check
      CHECK ((turno = ANY (ARRAY['M'::text, 'MD'::text, 'T'::text, 'N'::text]))),
    CONSTRAINT novedades_texto_check
      CHECK (((char_length(btrim(texto)) >= 1) AND (char_length(texto) <= 2000)))
);
CREATE INDEX novedades_fecha_idx ON horarios.novedades USING btree (fecha DESC, creado_en DESC);
CREATE INDEX novedades_ambiente_idx ON horarios.novedades USING btree (ambiente_id);

ALTER TABLE horarios.reportes_turno
  ADD COLUMN estado text DEFAULT 'validado'::text NOT NULL,
  ADD COLUMN validado_por uuid REFERENCES horarios.perfiles(id) ON DELETE SET NULL,
  ADD COLUMN validado_en timestamp with time zone DEFAULT now(),
  ADD CONSTRAINT reportes_turno_estado_check
    CHECK ((estado = ANY (ARRAY['pendiente'::text, 'validado'::text, 'rechazado'::text]))),
  ADD CONSTRAINT reportes_turno_validacion_check
    CHECK (((estado = 'pendiente'::text) = (validado_en IS NULL)));
-- Existing reports were filled as validado above; new ones start pendiente.
ALTER TABLE horarios.reportes_turno
  ALTER COLUMN estado SET DEFAULT 'pendiente'::text,
  ALTER COLUMN validado_en DROP DEFAULT;
CREATE INDEX reportes_turno_estado_idx ON horarios.reportes_turno USING btree (estado, creado_en DESC);

-- A decided report whose content changes must be decided again.
CREATE FUNCTION horarios.fn_trg_reporte_estado() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'horarios'
    AS $$
begin
  if old.estado <> 'pendiente' and new.estado = old.estado
     and ((new.turno, new.novedades) is distinct from (old.turno, old.novedades)
          or (new.foto_path is not null and new.foto_path is distinct from old.foto_path)) then
    new.estado := 'pendiente';
    new.validado_por := null;
    new.validado_en := null;
  end if;
  return new;
end $$;

CREATE TRIGGER trg_reportes_turno_estado BEFORE UPDATE ON horarios.reportes_turno
  FOR EACH ROW EXECUTE FUNCTION horarios.fn_trg_reporte_estado();

-- Validate or reject a pending shift close (Jefe/Encargado, never their own).
CREATE FUNCTION horarios.fn_decidir_reporte(p_reporte bigint, p_estado text) RETURNS void
    LANGUAGE plpgsql
    SET search_path TO 'horarios'
    AS $$
declare r horarios.reportes_turno;
begin
  if not horarios.fn_puede_gestionar_auxiliares() then
    raise exception 'No tiene permisos para realizar esta acción.' using errcode = '42501';
  end if;
  if p_estado not in ('validado', 'rechazado') then
    raise exception 'El estado debe ser validado o rechazado.';
  end if;
  select * into r from horarios.reportes_turno where id = p_reporte for update;
  if not found then
    raise exception 'No encontrado.' using errcode = 'P0002';
  end if;
  if r.auxiliar_id = horarios.fn_usuario_actual() then
    raise exception 'No puede validar su propio cierre de turno.' using errcode = '42501';
  end if;
  if r.estado <> 'pendiente' then
    raise exception 'Este cierre ya fue %.', r.estado;
  end if;
  update horarios.reportes_turno
     set estado = p_estado,
         validado_por = horarios.fn_usuario_actual(),
         validado_en = now()
   where id = p_reporte;
end $$;
"""

DOWNGRADE = r"""
DROP FUNCTION horarios.fn_decidir_reporte(bigint, text);
DROP TRIGGER trg_reportes_turno_estado ON horarios.reportes_turno;
DROP FUNCTION horarios.fn_trg_reporte_estado();
DROP INDEX horarios.reportes_turno_estado_idx;
ALTER TABLE horarios.reportes_turno
  DROP CONSTRAINT reportes_turno_validacion_check,
  DROP CONSTRAINT reportes_turno_estado_check,
  DROP COLUMN validado_en,
  DROP COLUMN validado_por,
  DROP COLUMN estado;
DROP TABLE horarios.novedades;
"""


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
