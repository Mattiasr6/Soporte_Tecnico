"""Link Soporte users (`Usuarios`) to asignacion perfiles (`horarios.perfiles`).

`Usuarios` is the single source of truth: every authenticated asignacion request
re-syncs the perfil's rol, activo and nombre from it.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

# Usuarios.Role -> perfiles.rol. Tecnico has no asignacion equivalent, so it gets
# the least privileged rol. Unknown roles fall back to the same.
ROLE_MAP: dict[str, str] = {
    "Jefe": "admin",
    "Encargado": "encargado",
    "Auxiliar": "auxiliar",
    "Tecnico": "invitado",
}
DEFAULT_ROL = "invitado"
# perfiles_textos_check: nombre_completo is 1..120 chars after trim.
NOMBRE_MAX = 120


def map_role(role: str) -> str:
    return ROLE_MAP.get(role, DEFAULT_ROL)


_LINK_BY_CORREO = text(
    """
    update horarios.perfiles
       set usuario_id = :usuario_id
     where usuario_id is null
       and lower(correo) = lower(:correo)
       and not exists (
             select 1 from horarios.perfiles where usuario_id = :usuario_id
           )
    """
)

# Only touches the row when something changed, so a read-only request does not
# bump actualizado_en on every call.
_UPSERT = text(
    """
    insert into horarios.perfiles (usuario_id, nombre_completo, correo, rol, activo)
    values (:usuario_id, :nombre, :correo, :rol, :activo)
    on conflict (usuario_id) do update
       set nombre_completo = excluded.nombre_completo,
           correo = excluded.correo,
           rol = excluded.rol,
           activo = excluded.activo
     where (perfiles.nombre_completo, perfiles.correo, perfiles.rol, perfiles.activo)
           is distinct from
           (excluded.nombre_completo, excluded.correo, excluded.rol, excluded.activo)
    returning id
    """
)

_SELECT_ID = text("select id from horarios.perfiles where usuario_id = :usuario_id")


def ensure_perfil(db: Session, usuario: Usuario) -> UUID:
    """Create or re-sync the perfil of `usuario` and return its id.

    Must run BEFORE the request's `app.usuario_id` context is set: the perfiles
    trigger `fn_trg_proteger_admin` forbids an admin from demoting themself, and
    that guard keys on `fn_usuario_actual()`. Without the context the sync is not
    "self", so a role change made in Usuarios always wins. The caller commits.
    """
    nombre = (usuario.display_name or "").strip()[:NOMBRE_MAX] or usuario.email
    params = {
        "usuario_id": usuario.id,
        "nombre": nombre,
        "correo": usuario.email,
        "rol": map_role(usuario.role),
        "activo": bool(usuario.activo),
    }
    # A perfil imported without a link (same correo) is adopted, not duplicated.
    db.execute(_LINK_BY_CORREO, params)
    perfil_id = db.execute(_UPSERT, params).scalar()
    if perfil_id is None:
        perfil_id = db.execute(_SELECT_ID, params).scalar_one()
    return perfil_id
