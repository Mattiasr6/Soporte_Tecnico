"""Auditoría de cambios esenciales. Solo un Jefe puede leerla."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.errors import forbidden
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.auditoria import AuditoriaCambio

router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])


@router.get("")
def listar(
    db: DbSession,
    user: CurrentUser,
    limite: int = Query(default=200, ge=1, le=1000),
    entidad: str | None = Query(default=None, max_length=50),
    accion: str | None = Query(default=None, max_length=50),
) -> list[dict[str, object]]:
    # Jefe o con dashboard (el dev es Técnico con ese flag). Encargado y
    # Auxiliar no lo tienen -> 403. Verificado contra Usuarios.CanViewDashboard.
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede ver la auditoría")
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
