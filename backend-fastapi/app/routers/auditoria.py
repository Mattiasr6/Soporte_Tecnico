"""Auditoría de cambios esenciales. Solo un Jefe puede leerla."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.errors import forbidden
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.auditoria import AuditoriaCambio

router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])


def _solo_jefe(user: CurrentUser) -> None:
    """Gate estricto por rol.

    OJO: no es `is_privileged`, que además deja pasar a cualquiera con
    `can_view_dashboard` (los Encargados). La auditoría es solo de Jefes.
    """
    if user.role != "Jefe":
        raise forbidden("Solo un jefe puede ver la auditoría")


@router.get("")
def listar(
    db: DbSession,
    user: CurrentUser,
    limite: int = Query(default=200, ge=1, le=1000),
    entidad: str | None = Query(default=None, max_length=50),
    accion: str | None = Query(default=None, max_length=50),
) -> list[dict[str, object]]:
    _solo_jefe(user)
    q = select(AuditoriaCambio).order_by(
        AuditoriaCambio.fecha.desc(), AuditoriaCambio.id.desc()
    )
    if entidad:
        q = q.where(AuditoriaCambio.entidad == entidad)
    if accion:
        q = q.where(AuditoriaCambio.accion == accion)
    filas = db.scalars(q.limit(limite)).all()
    return [
        {
            "id": r.id,
            "fecha": r.fecha.isoformat(),
            "usuario_email": r.usuario_email,
            "usuario_nombre": r.usuario_nombre,
            "rol": r.rol,
            "accion": r.accion,
            "entidad": r.entidad,
            "entidad_id": r.entidad_id,
            "detalle": r.detalle,
        }
        for r in filas
    ]
