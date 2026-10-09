-- Schema for the ported ASIGNACION (frontend-horarios) data model.
CREATE SCHEMA horarios;

-- Replacement for Supabase auth.uid(): FastAPI runs
--   SET LOCAL app.usuario_id = '<Usuarios.Id>'
-- inside each request transaction. Returns the linked perfil id, or NULL when
-- the setting is absent, empty, not an integer, or not linked to any perfil.
CREATE FUNCTION horarios.fn_usuario_actual() RETURNS uuid
    LANGUAGE sql STABLE
    SET search_path TO 'horarios'
    AS $$
  select p.id
    from horarios.perfiles p
   where p.usuario_id = (
           select case when s ~ '^[0-9]{1,9}$' then s::integer end
             from (select current_setting('app.usuario_id', true) as s) v
         );
$$;
