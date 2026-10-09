"""User management of the asignacion app (old Supabase `perfiles` screen).

Soporte `Usuarios` is the single identity source, so create, rol, activo,
nombre and password are written there through the same functions as
`/api/usuarios`; the perfil is then re-synced with `ensure_perfil`. Only the
asignacion-only fields (turno_habitual, sabado_rotativo) are written to
`horarios.perfiles` directly.

Why a thin endpoint instead of calling `/api/usuarios` from Angular: the screen
needs perfil ids and asignacion fields next to the identity (and the correo,
which `/api/usuarios` does not return), and the rol <-> Role translation (with
its Tecnico rule) belongs on the server, in one place with ROLE_MAP.

Permission: admin only (`fn_es_admin`), like the old `fn_crear_usuario`,
`fn_cambiar_password` and the `perfiles_editar` policy. The asignacion admin is
a Soporte Jefe, who also passes the Soporte rule for user management.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.db.asignacion import AsignacionDb
from app.models.usuario import Usuario
from app.routers.usuarios import (
    aplicar_activo,
    aplicar_nombre,
    aplicar_password,
    aplicar_rol,
    buscar_usuario,
    crear,
)
from app.schemas.asignacion_usuarios import (
    PasswordIn,
    UsuarioAsignacionCreateIn,
    UsuarioAsignacionOut,
    UsuarioAsignacionUpdateIn,
)
from app.schemas.usuario import UsuarioCreateIn
from app.services.asignacion.sql import Permission, not_found, require, writing
from app.services.asignacion_perfiles import ROL_TO_ROLE, ensure_perfil, map_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuarios")

_SELECT = """
    select p.id, p.usuario_id, p.nombre_completo, p.correo, p.rol, u."Role" as role,
           p.activo, p.turno_habitual, p.sabado_rotativo
      from horarios.perfiles p
      join "Usuarios" u on u."Id" = p.usuario_id
"""
_LIST = text(_SELECT + " order by p.nombre_completo, p.id")
_ONE = text(_SELECT + " where p.id = :id")
_USUARIO_DE_PERFIL = text(
    "select usuario_id from horarios.perfiles where id = :id and usuario_id is not null"
)
_PERFIL_CAMPOS = ("turno_habitual", "sabado_rotativo")


def _sync_all(db: Session) -> None:
    """Give every Soporte user an up-to-date perfil, so new users show up here.

    One savepoint per user: a single bad row (e.g. a correo already taken by
    another perfil) is logged and skipped instead of hiding the whole list.
    """
    for usuario in db.scalars(select(Usuario)).all():
        try:
            with db.begin_nested():
                ensure_perfil(db, usuario)
        except DBAPIError:
            logger.warning("perfil sync skipped for usuario %s", usuario.id)


def _perfil_row(db: Session, perfil_id: UUID) -> dict[str, Any]:
    row = db.execute(_ONE, {"id": perfil_id}).mappings().one_or_none()
    if row is None:
        raise not_found()
    return dict(row)


def _usuario_de(db: Session, perfil_id: UUID) -> Usuario:
    usuario_id = db.execute(_USUARIO_DE_PERFIL, {"id": perfil_id}).scalar()
    if usuario_id is None:
        raise not_found()
    return buscar_usuario(db, usuario_id)


@router.get("", response_model=list[UsuarioAsignacionOut])
def listar(db: AsignacionDb) -> list[dict[str, Any]]:
    require(db, Permission.ADMIN)
    with writing(db):
        _sync_all(db)
    return [dict(r) for r in db.execute(_LIST).mappings().all()]


@router.post("", response_model=UsuarioAsignacionOut, status_code=201)
def crear_usuario(dto: UsuarioAsignacionCreateIn, db: AsignacionDb) -> dict[str, Any]:
    require(db, Permission.ADMIN)
    with writing(db):
        nuevo = crear(
            db,
            UsuarioCreateIn(
                email=dto.correo,
                display_name=dto.nombre_completo,
                role=ROL_TO_ROLE[dto.rol],
                password=dto.password,
                activo=True,
            ),
        )
        perfil_id = ensure_perfil(db, nuevo)
    return _perfil_row(db, perfil_id)


@router.patch("/{perfil_id}", response_model=UsuarioAsignacionOut)
def actualizar(
    perfil_id: UUID,
    dto: UsuarioAsignacionUpdateIn,
    db: AsignacionDb,
    user: CurrentUser,
) -> dict[str, Any]:
    require(db, Permission.ADMIN)
    target = _usuario_de(db, perfil_id)
    cambios = dto.model_fields_set
    with writing(db):
        # A Tecnico shows as "invitado": keeping that rol must not rewrite the
        # Role, so it is only written when the asignacion rol really changes.
        if dto.rol is not None and dto.rol != map_role(target.role):
            aplicar_rol(user.id, target, ROL_TO_ROLE[dto.rol])
        if dto.activo is not None and dto.activo != target.activo:
            aplicar_activo(user.id, target, dto.activo)
        if dto.nombre_completo is not None:
            aplicar_nombre(target, dto.nombre_completo)
        db.flush()
        ensure_perfil(db, target)
        valores = {c: getattr(dto, c) for c in _PERFIL_CAMPOS if c in cambios}
        if valores:
            asignaciones = ", ".join(f"{c} = :{c}" for c in valores)
            db.execute(
                text(f"update horarios.perfiles set {asignaciones} where id = :id"),
                {**valores, "id": perfil_id},
            )
    return _perfil_row(db, perfil_id)


@router.post("/{perfil_id}/password", status_code=204)
def cambiar_password(perfil_id: UUID, dto: PasswordIn, db: AsignacionDb) -> None:
    require(db, Permission.ADMIN)
    target = _usuario_de(db, perfil_id)
    with writing(db):
        aplicar_password(target, dto.password)
