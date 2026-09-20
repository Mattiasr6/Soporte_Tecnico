from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.schemas.horario import AsignarIn, CoberturaFranja, CoberturaOut, HorarioOut

router = APIRouter(prefix="/api/horarios", tags=["horarios"])

FRANJAS = (
    ("Manana", "08:00", "12:00"),
    ("Medio dia", "12:00", "14:30"),
    ("Tarde", "14:30", "18:30"),
    ("Noche", "18:30", "20:00"),
)


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


@router.get("", response_model=list[HorarioOut])
def get_all(
    db: DbSession, user: CurrentUser, mes: int | None = None, anio: int | None = None
):
    q = select(Horario, Usuario.display_name).join(
        Usuario, Usuario.id == Horario.usuario_id
    )
    if mes is not None:
        q = q.where(Horario.mes == mes)
    if anio is not None:
        q = q.where(Horario.anio == anio)
    if user.role != "Jefe":
        q = q.where(Horario.usuario_id == user.id)
    rows = db.execute(q.order_by(Usuario.display_name)).all()
    return [
        {
            "id": h.id,
            "usuario_id": h.usuario_id,
            "nombre": nombre,
            "label": h.label,
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
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede asignar horarios")
    tecnico = db.get(Usuario, dto.usuario_id)
    if tecnico is None or tecnico.role != "Tecnico":
        raise bad_request("Tecnico no encontrado")
    existente = db.scalars(
        select(Horario).where(
            Horario.usuario_id == dto.usuario_id,
            Horario.mes == dto.mes,
            Horario.anio == dto.anio,
        )
    ).first()
    if existente is not None:
        existente.label = dto.label
        existente.hora_inicio1 = dto.hora_inicio1
        existente.hora_fin1 = dto.hora_fin1
        existente.hora_inicio2 = dto.hora_inicio2
        existente.hora_fin2 = dto.hora_fin2
    else:
        db.add(
            Horario(
                usuario_id=dto.usuario_id,
                label=dto.label,
                hora_inicio1=dto.hora_inicio1,
                hora_fin1=dto.hora_fin1,
                hora_inicio2=dto.hora_inicio2,
                hora_fin2=dto.hora_fin2,
                mes=dto.mes,
                anio=dto.anio,
                created_at=datetime.now(timezone.utc),
            )
        )
    db.commit()


@router.delete("/{horario_id}", status_code=204)
def eliminar(horario_id: int, db: DbSession, user: CurrentUser) -> None:
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede eliminar horarios")
    horario = db.get(Horario, horario_id)
    if horario is None:
        raise not_found("Horario no encontrado")
    db.delete(horario)
    db.commit()


@router.get("/cobertura", response_model=CoberturaOut)
def get_cobertura(
    db: DbSession,
    user: CurrentUser,
    mes: int | None = None,
    anio: int | None = None,
):
    now = datetime.now(timezone.utc)
    target_mes = mes if mes is not None else now.month
    target_anio = anio if anio is not None else now.year
    rows = db.execute(
        select(Horario, Usuario.display_name)
        .join(Usuario, Usuario.id == Horario.usuario_id)
        .where(Horario.mes == target_mes, Horario.anio == target_anio)
    ).all()
    cobertura = [
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
    return CoberturaOut(mes=target_mes, anio=target_anio, cobertura=cobertura)
