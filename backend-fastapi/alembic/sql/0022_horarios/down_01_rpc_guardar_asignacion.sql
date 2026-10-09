-- Downgrade of 0022: restores rpc_guardar_asignacion exactly as 0021 created it
-- (copied verbatim from alembic/sql/0021_horarios/02_schema.sql), which ignores
-- p.reubicaciones. Reubicaciones already saved through 0022 stay in place.

CREATE OR REPLACE FUNCTION horarios.rpc_guardar_asignacion(p jsonb) RETURNS bigint
    LANGUAGE plpgsql
    SET search_path TO 'horarios'
    AS $$
declare
  v_id     bigint := nullif(p->>'id', '')::bigint;
  v_modo   text;
  v_inicio date;
  v_fin    date;
  v_ids    bigint[];
  h        jsonb;
begin
  if jsonb_array_length(coalesce(p->'horarios', '[]')) = 0 then
    raise exception 'Debe registrar al menos un horario (día, hora y laboratorio).';
  end if;

  select modo_fechas into v_modo from horarios.sistemas_academicos where id = (p->>'sistema_id')::bigint;
  if v_modo is null then
    raise exception 'Seleccione el sistema (modular o semestral).';
  end if;

  -- Rango: en modular sale de los días marcados
  if v_modo = 'dias' then
    if jsonb_array_length(coalesce(p->'fechas', '[]')) = 0 then
      raise exception 'Marque en el calendario los días de clase.';
    end if;
    select min((x #>> '{}')::date), max((x #>> '{}')::date) into v_inicio, v_fin
    from jsonb_array_elements(p->'fechas') x;
  else
    v_inicio := nullif(p->>'fecha_inicio', '')::date;
    v_fin    := nullif(p->>'fecha_fin', '')::date;
    if v_inicio is null or v_fin is null then
      raise exception 'Indique la fecha de inicio y de fin.';
    end if;
  end if;

  if v_id is null then
    insert into horarios.asignaciones (sistema_id, docente_id, materia_id, carrera_id, grupo, fecha_inicio, fecha_fin, observacion)
    values ((p->>'sistema_id')::bigint, (p->>'docente_id')::bigint, (p->>'materia_id')::bigint, (p->>'carrera_id')::bigint,
            nullif(p->>'grupo', ''), v_inicio, v_fin, nullif(p->>'observacion', ''))
    returning id into v_id;
  else
    update horarios.asignaciones set
      sistema_id   = (p->>'sistema_id')::bigint,
      docente_id   = (p->>'docente_id')::bigint,
      materia_id   = (p->>'materia_id')::bigint,
      carrera_id   = (p->>'carrera_id')::bigint,
      grupo        = nullif(p->>'grupo', ''),
      fecha_inicio = v_inicio,
      fecha_fin    = v_fin,
      observacion  = nullif(p->>'observacion', '')
    where id = v_id;
    if not found then
      raise exception 'La asignación % no existe.', v_id;
    end if;
  end if;

  -- Días marcados (se reemplazan)
  delete from horarios.asignacion_fechas where asignacion_id = v_id;
  if v_modo = 'dias' then
    insert into horarios.asignacion_fechas (asignacion_id, fecha)
    select distinct v_id, (x #>> '{}')::date from jsonb_array_elements(p->'fechas') x;
  end if;

  -- Se eliminan los horarios que ya no vienen (sus cesiones/reubicaciones caen en cascada)
  select coalesce(array_agg((x->>'id')::bigint), '{}') into v_ids
  from jsonb_array_elements(p->'horarios') x where nullif(x->>'id', '') is not null;

  delete from horarios.asignacion_horarios where asignacion_id = v_id and not (id = any(v_ids));

  for h in select * from jsonb_array_elements(p->'horarios') loop
    if nullif(h->>'id', '') is null then
      insert into horarios.asignacion_horarios (asignacion_id, dia_semana, hora_inicio, hora_fin, ambiente_id)
      values (v_id, (h->>'dia_semana')::smallint, (h->>'hora_inicio')::time, (h->>'hora_fin')::time, (h->>'ambiente_id')::bigint);
    else
      update horarios.asignacion_horarios set
        dia_semana  = (h->>'dia_semana')::smallint,
        hora_inicio = (h->>'hora_inicio')::time,
        hora_fin    = (h->>'hora_fin')::time,
        ambiente_id = (h->>'ambiente_id')::bigint
      where id = (h->>'id')::bigint and asignacion_id = v_id;
    end if;
  end loop;

  return v_id;
end $$;
