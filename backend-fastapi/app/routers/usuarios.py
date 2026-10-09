from datetime import UTC, datetime, time

import bcrypt
from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    PasswordResetIn,
    RolIn,
    SesionIn,
    UsuarioCreateIn,
    UsuarioOut,
)
from app.services.estados import estado_efectivo
from app.services.horarios import LA_PAZ, esta_fuera_de_horario

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

ESTADOS_VALIDOS = {"disponible": "Disponible", "ocupado": "Ocupado"}
# Decano and Invitado exist for the asignacion module (horarios.perfiles roles).
# Their Soporte permissions are not defined yet: no check grants them anything,
# so they only get the default (least privileged) behavior.
ROLES_VALIDOS = ("Tecnico", "Jefe", "Auxiliar", "Encargado", "Decano", "Invitado")
ROL_INVALIDO = "Rol inválido. Use: " + ", ".join(ROLES_VALIDOS)


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


# --- User management -----------------------------------------------------------
# Shared with the asignacion module (`routers/asignacion/usuarios.py`), so both
# screens apply the same rules. They validate and mutate but never commit or check
# permissions: callers do both.


def buscar_usuario(db: Session, usuario_id: int) -> Usuario:
    target = db.get(Usuario, usuario_id)
    if target is None:
        raise not_found("Usuario no encontrado")
    return target


def _validar_password(password: str) -> None:
    if len(password) < MINIMO_PASSWORD:
        raise bad_request(
            f"La contraseña necesita al menos {MINIMO_PASSWORD} caracteres"
        )


def _validar_nombre(display_name: str) -> str:
    nombre = display_name.strip()
    if not nombre:
        raise bad_request("El nombre es obligatorio")
    if len(nombre) > 255:
        raise bad_request("El nombre no puede superar 255 caracteres")
    return nombre


def crear(db: Session, dto: UsuarioCreateIn) -> Usuario:
    """Validate and add a new user (flushed, so it already has an id)."""
    email = dto.email.strip().lower()
    if not email:
        raise bad_request("El email es obligatorio")
    nombre = _validar_nombre(dto.display_name)
    if dto.role not in ROLES_VALIDOS:
        raise bad_request(ROL_INVALIDO)
    if dto.password is not None:
        _validar_password(dto.password)
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
    db.flush()
    return nuevo


def aplicar_activo(actor_id: int, target: Usuario, activo: bool) -> None:
    if target.id == actor_id and not activo:
        raise bad_request("No puedes desactivar tu propio usuario")
    target.activo = activo
    target.updated_at = datetime.now(UTC)


def aplicar_rol(actor_id: int, target: Usuario, role: str) -> None:
    if target.id == actor_id:
        raise bad_request("No puedes cambiar tu propio rol")
    if role not in ROLES_VALIDOS:
        raise bad_request(ROL_INVALIDO)
    target.role = role
    target.updated_at = datetime.now(UTC)


def aplicar_password(target: Usuario, password: str) -> None:
    _validar_password(password)
    target.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    target.updated_at = datetime.now(UTC)


def aplicar_nombre(target: Usuario, display_name: str) -> None:
    target.display_name = _validar_nombre(display_name)
    target.updated_at = datetime.now(UTC)


def _salida(target: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=target.id,
        display_name=target.display_name,
        especialidad=target.especialidad,
        role=target.role,
        estado_actual=target.estado_actual,
        activo=target.activo,
    )


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(dto: UsuarioCreateIn, db: DbSession, user: CurrentUser):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    nuevo = crear(db, dto)
    db.commit()
    db.refresh(nuevo)
    return _salida(nuevo)


@router.patch("/{usuario_id}/activo", response_model=UsuarioOut)
def cambiar_activo(usuario_id: int, dto: ActivoIn, db: DbSession, user: CurrentUser):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    if usuario_id == user.id and not dto.activo:
        raise bad_request("No puedes desactivar tu propio usuario")
    target = buscar_usuario(db, usuario_id)
    aplicar_activo(user.id, target, dto.activo)
    db.commit()
    db.refresh(target)
    return _salida(target)


@router.patch("/{usuario_id}/rol", response_model=UsuarioOut)
def cambiar_rol(usuario_id: int, dto: RolIn, db: DbSession, user: CurrentUser):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    if usuario_id == user.id:
        raise bad_request("No puedes cambiar tu propio rol")
    if dto.role not in ROLES_VALIDOS:
        raise bad_request(ROL_INVALIDO)
    target = buscar_usuario(db, usuario_id)
    aplicar_rol(user.id, target, dto.role)
    db.commit()
    db.refresh(target)
    return _salida(target)


@router.post("/{usuario_id}/reset-password", status_code=204)
def reset_password(
    usuario_id: int, dto: PasswordResetIn, db: DbSession, user: CurrentUser
):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede gestionar usuarios")
    _validar_password(dto.password)
    target = buscar_usuario(db, usuario_id)
    aplicar_password(target, dto.password)
    db.commit()


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
