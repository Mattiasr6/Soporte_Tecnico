from datetime import UTC, datetime, time

import bcrypt
from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.atencion import Atencion
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.realtime.hub import broadcast
from app.routers.auth import MINIMO_PASSWORD
from app.schemas.usuario import (
    ActivoIn,
    EspecialidadIn,
    EstadoIn,
    NotasIn,
    NotasOut,
    SesionIn,
    UsuarioCreateIn,
    UsuarioOut,
)
from app.services.estados import estado_efectivo
from app.services.horarios import LA_PAZ, esta_fuera_de_horario

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

ESTADOS_VALIDOS = {"disponible": "Disponible", "ocupado": "Ocupado"}
ROLES_VALIDOS = ("Tecnico", "Jefe", "Auxiliar")


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
def get_all(db: DbSession, user: CurrentUser, incluir_inactivos: bool = False):
    now = datetime.now(UTC)
    consulta = select(Usuario)
    if not incluir_inactivos:
        consulta = consulta.where(
            Usuario.role.in_(["Tecnico", "Jefe"]), Usuario.activo.is_(True)
        )
    usuarios = db.scalars(consulta.order_by(Usuario.display_name)).all()
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
                activo=u.activo,
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
        activo=usuario.activo,
    )


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(dto: UsuarioCreateIn, db: DbSession, user: CurrentUser):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    email = dto.email.strip().lower()
    if not email:
        raise bad_request("El email es obligatorio")
    nombre = dto.display_name.strip()
    if not nombre:
        raise bad_request("El nombre es obligatorio")
    if len(nombre) > 255:
        raise bad_request("El nombre no puede superar 255 caracteres")
    if dto.role not in ROLES_VALIDOS:
        raise bad_request("Rol inválido. Use: Tecnico, Jefe, Auxiliar")
    if dto.password is not None and len(dto.password) < MINIMO_PASSWORD:
        raise bad_request(
            f"La contraseña necesita al menos {MINIMO_PASSWORD} caracteres"
        )
    existe = db.scalars(
        select(Usuario).where(func.lower(Usuario.email) == email)
    ).first()
    if existe is not None:
        raise conflict("Email ya registrado")
    now = datetime.now(UTC)
    nuevo = Usuario(
        email=email,
        display_name=nombre,
        role=dto.role,
        password_hash=(
            bcrypt.hashpw(dto.password.encode(), bcrypt.gensalt()).decode()
            if dto.password
            else None
        ),
        estado_actual="Ausente",
        activo=dto.activo,
        created_at=now,
        updated_at=now,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return UsuarioOut(
        id=nuevo.id,
        display_name=nuevo.display_name,
        especialidad=nuevo.especialidad,
        role=nuevo.role,
        estado_actual=nuevo.estado_actual,
        activo=nuevo.activo,
    )


@router.patch("/{usuario_id}/activo", response_model=UsuarioOut)
def cambiar_activo(usuario_id: int, dto: ActivoIn, db: DbSession, user: CurrentUser):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    if usuario_id == user.id and not dto.activo:
        raise bad_request("No puedes desactivar tu propio usuario")
    target = db.get(Usuario, usuario_id)
    if target is None:
        raise not_found("Usuario no encontrado")
    target.activo = dto.activo
    target.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(target)
    return UsuarioOut(
        id=target.id,
        display_name=target.display_name,
        especialidad=target.especialidad,
        role=target.role,
        estado_actual=target.estado_actual,
        activo=target.activo,
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
