"""Schema `horarios`: turno and medio_solicitud on atenciones, lab dashboard.

Django stores both on every lab attention (Soporte `LabAtenciones.Turno` and
`MedioSolicitud`). They are ported onto `horarios.atenciones` with horarios
semantics:

- `turno` uses the horarios codes M/MD/T/N (Django: mañana/mediodia/tarde/
  noche). When the insert does not give it, trigger `trg_atenciones_turno`
  takes the turno of the linked work shift (`turno_trabajo_id`), or else the
  turno whose `horarios_turno` hours hold the ticket time (La Paz), with the
  same rule as fn_dashboard_detalle's `tickets_por_turno` (the latest started
  turno still running; before the first turno starts, 'N'). Existing rows are
  backfilled the same way (without touching `actualizado_en`).
- `medio_solicitud` takes Django's values ('Presencial', 'WhatsApp'), default
  'Presencial'.

`fn_dashboard_laboratorios` mirrors Django `lab_dashboard_vista` and
`lab_reportes_vista`: totals, top lab and turno, active auxiliares, per lab
(top tipo, top turno), counts by tipo, turno and medio, and the year trend,
with optional turno and ambiente filters. Same permission as the other
fn_dashboard_* functions (fn_puede_gestionar_auxiliares).

Revision ID: 0024_horarios_turno_medio
Revises: 0023_horarios_rol_tecnico
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_horarios_turno_medio"
down_revision: str | None = "0023_horarios_rol_tecnico"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = r"""
ALTER TABLE horarios.atenciones
  ADD COLUMN turno text,
  ADD COLUMN medio_solicitud text DEFAULT 'Presencial'::text NOT NULL,
  ADD CONSTRAINT atenciones_turno_check
    CHECK ((turno = ANY (ARRAY['M'::text, 'MD'::text, 'T'::text, 'N'::text]))),
  ADD CONSTRAINT atenciones_medio_solicitud_check
    CHECK ((medio_solicitud = ANY (ARRAY['Presencial'::text, 'WhatsApp'::text])));

-- Turno (M/MD/T/N) whose horarios_turno hours hold a moment, in La Paz time.
CREATE FUNCTION horarios.fn_turno_horario_de(p_momento timestamp with time zone)
    RETURNS text
    LANGUAGE sql STABLE
    SET search_path TO 'horarios'
    AS $$
  select coalesce((select h.turno from horarios.horarios_turno h
                    where h.hora_inicio <= (p_momento at time zone 'America/La_Paz')::time
                    order by ((p_momento at time zone 'America/La_Paz')::time < h.hora_fin) desc,
                             h.hora_inicio desc
                    limit 1), 'N');
$$;

CREATE FUNCTION horarios.fn_trg_atencion_turno() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'horarios'
    AS $$
begin
  if new.turno is null then
    new.turno := coalesce(
      (select t.turno from horarios.turnos_trabajo t where t.id = new.turno_trabajo_id),
      horarios.fn_turno_horario_de(new.creado_en));
  end if;
  return new;
end $$;

CREATE TRIGGER trg_atenciones_turno BEFORE INSERT ON horarios.atenciones
  FOR EACH ROW EXECUTE FUNCTION horarios.fn_trg_atencion_turno();

-- Backfill without bumping actualizado_en.
ALTER TABLE horarios.atenciones DISABLE TRIGGER trg_atenciones_actualizado;
UPDATE horarios.atenciones a
   SET turno = coalesce(
         (select t.turno from horarios.turnos_trabajo t where t.id = a.turno_trabajo_id),
         horarios.fn_turno_horario_de(a.creado_en))
 WHERE a.turno IS NULL;
ALTER TABLE horarios.atenciones ENABLE TRIGGER trg_atenciones_actualizado;
ALTER TABLE horarios.atenciones ALTER COLUMN turno SET NOT NULL;

-- Lab dashboard / reports (Django lab_dashboard_vista + lab_reportes_vista).
CREATE FUNCTION horarios.fn_dashboard_laboratorios(
    p_desde date, p_hasta date, p_turno text DEFAULT NULL, p_ambiente_id bigint DEFAULT NULL)
    RETURNS jsonb
    LANGUAGE plpgsql STABLE
    SET search_path TO 'horarios'
    AS $$
declare
  v_zona constant text := 'America/La_Paz';
  v_anio date := date_trunc('year', p_hasta)::date;
  r jsonb;
begin
  if not horarios.fn_puede_gestionar_auxiliares() then
    raise exception 'Solo el administrador o el encargado pueden ver el dashboard.';
  end if;
  if p_desde is null or p_hasta is null or p_hasta < p_desde or (p_hasta - p_desde) > 400 then
    raise exception 'Rango de fechas inválido.';
  end if;
  if p_turno is not null and p_turno not in ('M', 'MD', 'T', 'N') then
    raise exception 'Turno inválido.';
  end if;

  with f as (   -- tickets matching the turno/lab filters, with their local day
    select a.*, (a.creado_en at time zone v_zona)::date as dia
      from horarios.atenciones a
     where (p_turno is null or a.turno = p_turno)
       and (p_ambiente_id is null or a.ambiente_id = p_ambiente_id)
  ),
  t as (select * from f where dia between p_desde and p_hasta),
  labs as (
    select am.id, am.codigo, am.color, count(*) as total
      from t join horarios.ambientes am on am.id = t.ambiente_id
     group by am.id, am.codigo, am.color
  ),
  turnos as (
    select h.turno, h.hora_inicio, (select count(*) from t where t.turno = h.turno) as total
      from horarios.horarios_turno h
  )
  select jsonb_build_object(
    'kpis', jsonb_build_object(
      'total', (select count(*) from t),
      'lab_top', (select jsonb_build_object('codigo', codigo, 'total', total)
                    from labs order by total desc, codigo limit 1),
      'turno_top', (select jsonb_build_object('turno', turno, 'total', total)
                      from turnos where total > 0 order by total desc, hora_inicio limit 1),
      'auxiliares_activos', (select count(distinct auxiliar_id) from t)
    ),
    'por_lab', (
      select coalesce(jsonb_agg(jsonb_build_object(
               'id', l.id, 'codigo', l.codigo, 'color', l.color, 'total', l.total,
               'top_tipo', (select t.tipo from t where t.ambiente_id = l.id
                             group by t.tipo order by count(*) desc, t.tipo limit 1),
               'top_turno', (select t.turno from t where t.ambiente_id = l.id
                              group by t.turno order by count(*) desc, t.turno limit 1)
             ) order by l.total desc, l.codigo), '[]')
        from labs l
    ),
    'por_tipo', (
      select coalesce(jsonb_agg(jsonb_build_object('tipo', tipo, 'total', n)
                                order by n desc, tipo), '[]')
        from (select tipo, count(*) n from t group by tipo) x
    ),
    'por_turno', (
      select coalesce(jsonb_agg(jsonb_build_object('turno', turno, 'total', total)
                                order by hora_inicio), '[]')
        from turnos
    ),
    'por_medio', (
      select coalesce(jsonb_agg(jsonb_build_object('medio', medio_solicitud, 'total', n)
                                order by n desc, medio_solicitud), '[]')
        from (select medio_solicitud, count(*) n from t group by medio_solicitud) x
    ),
    'por_mes', (   -- year trend: January .. the month of p_hasta
      select coalesce(jsonb_agg(jsonb_build_object(
               'mes', to_char(m, 'YYYY-MM'),
               'total', (select count(*) from f
                          where f.dia >= m::date and f.dia < (m + interval '1 month')::date
                            and f.dia <= p_hasta)
             ) order by m), '[]')
        from generate_series(v_anio, date_trunc('month', p_hasta)::date, interval '1 month') m
    )
  ) into r;
  return r;
end $$;
"""

DOWNGRADE = r"""
DROP FUNCTION horarios.fn_dashboard_laboratorios(date, date, text, bigint);
DROP TRIGGER trg_atenciones_turno ON horarios.atenciones;
DROP FUNCTION horarios.fn_trg_atencion_turno();
DROP FUNCTION horarios.fn_turno_horario_de(timestamp with time zone);
ALTER TABLE horarios.atenciones
  DROP CONSTRAINT atenciones_medio_solicitud_check,
  DROP CONSTRAINT atenciones_turno_check,
  DROP COLUMN medio_solicitud,
  DROP COLUMN turno;
"""


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(UPGRADE)


def downgrade() -> None:
    _run_sql(DOWNGRADE)
