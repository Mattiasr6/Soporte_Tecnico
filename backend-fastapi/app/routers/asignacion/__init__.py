"""Asignacion module (ex ASIGNACION_DE-HORARIOS, Postgres schema `horarios`).

The prefix is `/api/asignacion` because `/api/horarios` already serves the
technicians' work schedules.
"""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.errors import forbidden
from app.core.security import CurrentUser
from app.db.asignacion import AsignacionDb
from app.routers.asignacion import (
    catalogos,
    dashboards,
    horarios_academicos,
    objetos_perdidos,
    ocupacion,
    operacion,
    reportes,
    turnos,
)

router = APIRouter(prefix="/api/asignacion", tags=["asignacion"])
router.include_router(catalogos.router)
router.include_router(horarios_academicos.router)
router.include_router(ocupacion.router)
router.include_router(turnos.router)
router.include_router(reportes.router)
router.include_router(operacion.router)
router.include_router(objetos_perdidos.router)
router.include_router(dashboards.router)


class PerfilOut(BaseModel):
    usuario_id: int
    perfil_id: UUID
    nombre_completo: str
    correo: str
    rol: str | None
    activo: bool
    turno_habitual: str | None
    sabado_rotativo: bool


# Resolved through the session context, not by usuario_id, so the response also
# proves that fn_usuario_actual()/fn_rol_actual() see the requesting user.
_ME = text(
    """
    select p.id, p.nombre_completo, p.correo, horarios.fn_rol_actual() as rol,
           p.activo, p.turno_habitual, p.sabado_rotativo
      from horarios.perfiles p
     where p.id = horarios.fn_usuario_actual()
    """
)


@router.get("/me", response_model=PerfilOut)
def me(user: CurrentUser, db: AsignacionDb) -> PerfilOut:
    row = db.execute(_ME).one_or_none()
    if row is None:
        raise forbidden("Sin perfil de asignacion")
    return PerfilOut(
        usuario_id=user.id,
        perfil_id=row.id,
        nombre_completo=row.nombre_completo,
        correo=row.correo,
        rol=row.rol,
        activo=row.activo,
        turno_habitual=row.turno_habitual,
        sabado_rotativo=row.sabado_rotativo,
    )
