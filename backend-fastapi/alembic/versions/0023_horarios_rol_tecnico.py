"""Schema `horarios`: real `tecnico` rol for Soporte technicians.

A Soporte Tecnico used to map to `invitado` (no access). Now it gets its own
perfiles rol: it sees everything (fn_puede_ver already allows every rol but
invitado) and operates like an auxiliar (fn_puede_operar), with no academic
editing, no auxiliar management, no admin and no personal shift
(fn_puede_cerrar_turno and the dashboard auxiliar list stay auxiliar-only).

The downgrade turns `tecnico` perfiles back into `invitado` and restores the
0021 constraint and function.

Revision ID: 0023_horarios_rol_tecnico
Revises: 0022_horarios_reubica_choques
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_horarios_rol_tecnico"
down_revision: str | None = "0022_horarios_reubica_choques"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rol_check(roles: Sequence[str]) -> str:
    valores = ", ".join(f"'{r}'::text" for r in roles)
    return f"""
ALTER TABLE horarios.perfiles DROP CONSTRAINT perfiles_rol_check;
ALTER TABLE horarios.perfiles ADD CONSTRAINT perfiles_rol_check
  CHECK ((rol = ANY (ARRAY[{valores}])));
"""


def _puede_operar(roles: Sequence[str]) -> str:
    valores = ", ".join(f"'{r}'" for r in roles)
    return f"""
CREATE OR REPLACE FUNCTION horarios.fn_puede_operar() RETURNS boolean
    LANGUAGE sql STABLE
    SET search_path TO 'horarios'
    AS $$
  select coalesce(horarios.fn_rol_actual() in ({valores}), false);
$$;
"""


ROLES_0021 = ("admin", "auxiliar", "decano", "encargado", "invitado")
ROLES_0023 = (*ROLES_0021, "tecnico")
OPERAR_0021 = ("admin", "encargado", "auxiliar")
OPERAR_0023 = (*OPERAR_0021, "tecnico")


def _run_sql(sql: str) -> None:
    # Raw psycopg cursor, same as 0021: no placeholder parsing of "%" or ":".
    with op.get_bind().connection.driver_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _run_sql(_rol_check(ROLES_0023) + _puede_operar(OPERAR_0023))


def downgrade() -> None:
    _run_sql(
        "update horarios.perfiles set rol = 'invitado' where rol = 'tecnico';"
        + _puede_operar(OPERAR_0021)
        + _rol_check(ROLES_0021)
    )
