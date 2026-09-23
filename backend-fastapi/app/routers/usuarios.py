from datetime import UTC, datetime, time

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.atencion import Atencion
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.realtime.hub import broadcast
from app.schemas.usuario import (
    EspecialidadIn,
    EstadoIn,
    NotasIn,
    NotasOut,
    SesionIn,
    UsuarioOut,
)
from app.services.estados import estado_efectivo
from app.services.horarios import LA_PAZ, esta_fuera_de_horario

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

ESTADOS_VALIDOS = {"disponible": "Disponible", "ocupado": "Ocupado"}


def _hoy_local() -> tuple[int, int, int]:
    """(mes, anio, dia ISO) en hora de La Paz, que es donde aplican los horarios."""
    local = datetime.now(UTC).astimezone(LA_PAZ)
    return local.month, local.year, local.isoweekday()


def _horarios_de_hoy(db: DbSession) -> dict[int, Horario]:
    mes, anio, dia = _hoy_local()
    rows = db.scalars(
        select(Horario).where(
            Horario.mes == mes, Horario.anio == anio, Horario.dia_semana == dia
        )
    ).all()
    return {h.usuario_id: h for h in rows}


def _atenciones_de_hoy(db: DbSession) -> dict[int, int]:
    hoy = datetime.now(UTC).astimezone(LA_PAZ).date()
    rows = db.execute(
        select(Atencion.usuario_id, func.count())
        .where(Atencion.fecha_registro == hoy)
        .group_by(Atencion.usuario_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def _fuera_de_turno(horario: Horario | None, ahora_utc: datetime) -> bool:
    return horario is None or esta_fuera_de_horario(
        horario.hora_inicio1,
        horario.hora_fin1,
        horario.hora_inicio2,
        horario.hora_fin2,
        ahora_utc,
    )


def _entra_a_las(horario: Horario | None, ahora_utc: datetime) -> str | None:
    if not _fuera_de_turno(horario, ahora_utc) or horario is None:
        return None
    hora_local = ahora_utc.astimezone(LA_PAZ).time()
    for inicio in (horario.hora_inicio1, horario.hora_inicio2):
        if inicio and time.fromisoformat(inicio) > hora_local:
            return inicio
    return None


@router.get("", response_model=list[UsuarioOut])
def get_all(db: DbSession, user: CurrentUser):
    now = datetime.now(UTC)
    usuarios = db.scalars(
        select(Usuario).where(Usuario.role.in_(["Tecnico", "Jefe"]))
    ).all()
    horarios = _horarios_de_hoy(db)
    conteos = _atenciones_de_hoy(db)
    salida: list[UsuarioOut] = []
    for u in usuarios:
        horario = horarios.get(u.id)
        salida.append(
            UsuarioOut(
                id=u.id,
                display_name=u.display_name,
                especialidad=u.especialidad,
                role=u.role,
                estado_actual=estado_efectivo(u.estado_actual, horario, now),
                horario_hoy=horario.label if horario else None,
                entra_a_las=_entra_a_las(horario, now),
                atenciones_hoy=conteos.get(u.id, 0),
                puede_cambiar_estado=not _fuera_de_turno(horario, now),
            )
        )
    return salida


@router.get("/me", response_model=UsuarioOut)
def get_me(db: DbSession, user: CurrentUser):
    now = datetime.now(UTC)
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no registrado en el sistema.")
    horario = _horarios_de_hoy(db).get(user.id)
    return UsuarioOut(
        id=usuario.id,
        display_name=usuario.display_name,
        especialidad=usuario.especialidad,
        role=usuario.role,
        estado_actual=estado_efectivo(usuario.estado_actual, horario, now),
        horario_hoy=horario.label if horario else None,
        entra_a_las=_entra_a_las(horario, now),
        atenciones_hoy=_atenciones_de_hoy(db).get(user.id, 0),
        puede_cambiar_estado=not _fuera_de_turno(horario, now),
    )


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
    now = datetime.now(UTC)
    horario = _horarios_de_hoy(db).get(user.id)
    if _fuera_de_turno(horario, now):
        raise forbidden(
            "Estás fuera de turno. Tu estado se calcula solo, no se puede cambiar."
        )
    usuario.estado_actual = nuevo
    usuario.updated_at = now
    db.commit()
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


@router.post("/sesion", status_code=204)
async def sesion(dto: SesionIn, db: DbSession, user: CurrentUser) -> None:
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no registrado en el sistema.")
    if usuario.role == "Auxiliar":
        return
    now = datetime.now(UTC)
    cambio = False
    if dto.conectado and usuario.estado_actual == "Ausente":
        usuario.estado_actual = "Disponible"
        usuario.updated_at = now
        cambio = True
    elif not dto.conectado and usuario.estado_actual == "Disponible":
        usuario.estado_actual = "Ausente"
        usuario.updated_at = now
        cambio = True
    if not cambio:
        return
    db.commit()
    horario = _horarios_de_hoy(db).get(usuario.id)
    await broadcast(
        {
            "type": "status_changed",
            "usuario_id": usuario.id,
            "nombre": usuario.display_name,
            "estado": estado_efectivo(usuario.estado_actual, horario, now),
            "motivo": None,
            "colaborador_nombre": None,
            "timestamp": now.strftime("%H:%M"),
        }
    )
