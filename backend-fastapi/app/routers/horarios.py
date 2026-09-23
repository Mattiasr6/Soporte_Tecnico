from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.schemas.horario import (
    AsignarIn,
    AsignarLoteIn,
    CoberturaFranja,
    CoberturaOut,
    HorarioOut,
)

router = APIRouter(prefix="/api/horarios", tags=["horarios"])

FRANJAS = (
    ("Manana", "08:00", "12:00"),
    ("Medio dia", "12:00", "14:30"),
    ("Tarde", "14:30", "18:30"),
    ("Noche", "18:30", "20:00"),
)

LUNES = 1
SABADO = 6
ROLES_CON_HORARIO = ("Tecnico", "Jefe")


def _exigir_jefe(user) -> None:
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede administrar horarios")


def _label_de(
    inicio1: str | None, fin1: str | None, inicio2: str | None, fin2: str | None
) -> str:
    tramos = []
    if inicio1 and fin1:
        tramos.append(f"{inicio1}-{fin1}")
    if inicio2 and fin2:
        tramos.append(f"{inicio2}-{fin2}")
    return " + ".join(tramos) or "Sin horario"


def _tiene_cobertura(
    inicio1: str | None,
    fin1: str | None,
    inicio2: str | None,
    fin2: str | None,
    f_inicio: str,
    f_fin: str,
) -> bool:
    if inicio1 is None or fin1 is None:
        return False
    if inicio1 < f_fin and fin1 > f_inicio:
        return True
    if inicio2 is not None and fin2 is not None:
        return inicio2 < f_fin and fin2 > f_inicio
    return False


def _upsert(db: DbSession, dto: AsignarIn) -> None:
    if not 1 <= dto.dia_semana <= 7:
        raise bad_request("DiaSemana va de 1 (lunes) a 7 (domingo)")
    persona = db.get(Usuario, dto.usuario_id)
    if persona is None or persona.role not in ROLES_CON_HORARIO:
        raise bad_request("Solo se pueden asignar horarios a tecnicos y jefes")
    existente = db.scalars(
        select(Horario).where(
            Horario.usuario_id == dto.usuario_id,
            Horario.mes == dto.mes,
            Horario.anio == dto.anio,
            Horario.dia_semana == dto.dia_semana,
        )
    ).first()
    label = _label_de(dto.hora_inicio1, dto.hora_fin1, dto.hora_inicio2, dto.hora_fin2)
    if existente is not None:
        existente.label = label
        existente.hora_inicio1 = dto.hora_inicio1
        existente.hora_fin1 = dto.hora_fin1
        existente.hora_inicio2 = dto.hora_inicio2
        existente.hora_fin2 = dto.hora_fin2
        return
    db.add(
        Horario(
            usuario_id=dto.usuario_id,
            label=label,
            hora_inicio1=dto.hora_inicio1,
            hora_fin1=dto.hora_fin1,
            hora_inicio2=dto.hora_inicio2,
            hora_fin2=dto.hora_fin2,
            dia_semana=dto.dia_semana,
            mes=dto.mes,
            anio=dto.anio,
            created_at=datetime.now(UTC),
        )
    )


@router.get("", response_model=list[HorarioOut])
def get_all(
    db: DbSession,
    user: CurrentUser,
    mes: int | None = None,
    anio: int | None = None,
    dia_semana: int | None = None,
):
    q = select(Horario, Usuario.display_name).join(
        Usuario, Usuario.id == Horario.usuario_id
    )
    if mes is not None:
        q = q.where(Horario.mes == mes)
    if anio is not None:
        q = q.where(Horario.anio == anio)
    if dia_semana is not None:
        q = q.where(Horario.dia_semana == dia_semana)
    if not is_privileged(user):
        q = q.where(Horario.usuario_id == user.id)
    rows = db.execute(q.order_by(Usuario.display_name, Horario.dia_semana)).all()
    return [
        {
            "id": h.id,
            "usuario_id": h.usuario_id,
            "nombre": nombre,
            "label": h.label,
            "dia_semana": h.dia_semana,
            "hora_inicio1": h.hora_inicio1,
            "hora_fin1": h.hora_fin1,
            "hora_inicio2": h.hora_inicio2,
            "hora_fin2": h.hora_fin2,
            "mes": h.mes,
            "anio": h.anio,
        }
        for h, nombre in rows
    ]


@router.post("", status_code=204)
def asignar(dto: AsignarIn, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    _upsert(db, dto)
    db.commit()


@router.post("/lote", status_code=204)
def asignar_lote(dto: AsignarLoteIn, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    if not dto.asignaciones:
        raise bad_request("No hay horarios para guardar")
    for asignacion in dto.asignaciones:
        _upsert(db, asignacion)
    db.commit()


@router.delete("/{horario_id}", status_code=204)
def eliminar(horario_id: int, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    horario = db.get(Horario, horario_id)
    if horario is None:
        raise not_found("Horario no encontrado")
    db.delete(horario)
    db.commit()


@router.delete("", status_code=204)
def eliminar_dia(
    db: DbSession,
    user: CurrentUser,
    usuario_id: int,
    mes: int,
    anio: int,
    dia_semana: int,
) -> None:
    _exigir_jefe(user)
    filas = db.scalars(
        select(Horario).where(
            Horario.usuario_id == usuario_id,
            Horario.mes == mes,
            Horario.anio == anio,
            Horario.dia_semana == dia_semana,
        )
    ).all()
    for fila in filas:
        db.delete(fila)
    db.commit()


def _cobertura_dia(
    db: DbSession, mes: int, anio: int, dia: int
) -> list[CoberturaFranja]:
    rows = db.execute(
        select(Horario, Usuario.display_name)
        .join(Usuario, Usuario.id == Horario.usuario_id)
        .where(
            Horario.mes == mes,
            Horario.anio == anio,
            Horario.dia_semana == dia,
            Usuario.role == "Tecnico",
        )
    ).all()
    return [
        CoberturaFranja(
            franja=nombre,
            hora=f"{inicio} - {fin}",
            tecnicos=[
                nombre_u
                for h, nombre_u in rows
                if _tiene_cobertura(
                    h.hora_inicio1,
                    h.hora_fin1,
                    h.hora_inicio2,
                    h.hora_fin2,
                    inicio,
                    fin,
                )
            ],
        )
        for nombre, inicio, fin in FRANJAS
    ]


@router.get("/cobertura", response_model=CoberturaOut)
def get_cobertura(
    db: DbSession,
    user: CurrentUser,
    mes: int | None = None,
    anio: int | None = None,
):
    now = datetime.now(UTC)
    target_mes = mes if mes is not None else now.month
    target_anio = anio if anio is not None else now.year
    return CoberturaOut(
        mes=target_mes,
        anio=target_anio,
        laborable=_cobertura_dia(db, target_mes, target_anio, LUNES),
        sabado=_cobertura_dia(db, target_mes, target_anio, SABADO),
    )
