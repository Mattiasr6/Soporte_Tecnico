-- Supabase created perfiles rows from auth.users (same uuid). Here the id is
-- generated locally and the perfil is linked to the Soporte user instead.
ALTER TABLE horarios.perfiles
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE horarios.perfiles
    ADD COLUMN usuario_id integer;

ALTER TABLE ONLY horarios.perfiles
    ADD CONSTRAINT perfiles_usuario_id_key UNIQUE (usuario_id);

ALTER TABLE ONLY horarios.perfiles
    ADD CONSTRAINT perfiles_usuario_id_fkey FOREIGN KEY (usuario_id)
    REFERENCES public."Usuarios"("Id") ON DELETE SET NULL;
