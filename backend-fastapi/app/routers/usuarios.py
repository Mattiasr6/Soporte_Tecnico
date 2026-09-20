from datetime import datetime, timezone

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.realtime.hub import broadcast
from app.schemas.usuario import (
    EspecialidadIn,
    EstadoIn,
    NotasIn,
    NotasOut,
    UsuarioOut,
)
from app.services.estados import estado_efectivo
from fastapi import APIRouter
from sqlalchemy import select

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

ESTADOS_VALIDOS = {"disponible": "Disponible", "ocupado": "Ocupado"}


def _horarios_mes(db: DbSession) -> dict[int, Horario]:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Horario).where(Horario.mes == now.month, Horario.anio == now.year)
    ).all()
    return {h.usuario_id: h for h in rows}


@router.get("", response_model=list[UsuarioOut])
def get_all(db: DbSession, user: CurrentUser):
    now = datetime.now(timezone.utc)
    usuarios = db.scalars(
        select(Usuario).where(Usuario.role.in_(["Tecnico", "Jefe"]))
    ).all()
    horarios = _horarios_mes(db)
    return [
        {
            "id": u.id,
            "display_name": u.display_name,
            "especialidad": u.especialidad,
            "role": u.role,
            "estado_actual": estado_efectivo(u.estado_actual, horarios.get(u.id), now),
        }
        for u in usuarios
    ]


@router.get("/me", response_model=UsuarioOut)
def get_me(db: DbSession, user: CurrentUser):
    now = datetime.now(timezone.utc)
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no registrado en el sistema.")
    horario = db.scalars(
        select(Horario).where(
            Horario.usuario_id == user.id,
            Horario.mes == now.month,
            Horario.anio == now.year,
        )
    ).first()
    return {
        "id": usuario.id,
        "display_name": usuario.display_name,
        "especialidad": usuario.especialidad,
        "role": usuario.role,
        "estado_actual": estado_efectivo(usuario.estado_actual, horario, now),
    }


@router.patch("/{usuario_id}/especialidad", status_code=204)
def update_especialidad(
    usuario_id: int, dto: EspecialidadIn, db: DbSession, user: CurrentUser
) -> None:
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede editar especialidades")
    target = db.get(Usuario, usuario_id)
    if target is None:
        raise not_found("Usuario no encontrado")
    target.especialidad = dto.especialidad
    db.commit()


@router.get("/notas", response_model=NotasOut)
def get_notas(db: DbSession, user: CurrentUser):
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no encontrado")
    return {"contenido": usuario.notas}


@router.put("/notas", status_code=204)
def update_notas(dto: NotasIn, db: DbSession, user: CurrentUser) -> None:
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no encontrado")
    usuario.notas = dto.contenido
    db.commit()


@router.patch("/estado", status_code=204)
async def toggle_estado(dto: EstadoIn, db: DbSession, user: CurrentUser) -> None:
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no registrado en el sistema.")
    nuevo = ESTADOS_VALIDOS.get(dto.estado_actual.strip().lower())
    if nuevo is None:
        raise bad_request("Estado inválido. Use: disponible, ocupado")
    if nuevo == "Ausente":
        raise bad_request("No puedes cambiarte a ausente manualmente.")
    usuario.estado_actual = nuevo
    usuario.updated_at = datetime.now(timezone.utc)
    db.commit()
    now = datetime.now(timezone.utc)
    horario = db.scalars(
        select(Horario).where(
            Horario.usuario_id == user.id,
            Horario.mes == now.month,
            Horario.anio == now.year,
        )
    ).first()
    colaborador_nombre = None
    if dto.colaborador_id is not None:
        colab = db.get(Usuario, dto.colaborador_id)
        colaborador_nombre = colab.display_name if colab else None
    await broadcast(
        {
            "type": "status_changed",
            "usuario_id": usuario.id,
            "nombre": usuario.display_name,
            "estado": estado_efectivo(usuario.estado_actual, horario, now),
            "motivo": dto.motivo,
            "colaborador_nombre": colaborador_nombre,
            "timestamp": now.strftime("%H:%M"),
        }
    )
