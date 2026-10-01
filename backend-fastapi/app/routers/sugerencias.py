"""Buzón de sugerencias: todos proponen, solo Jefe cambia el estado."""

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.sugerencia import Sugerencia
from app.models.usuario import Usuario
from app.schemas.sugerencia import SugerenciaIn, SugerenciaOut, SugerenciaPatchIn

router = APIRouter(prefix="/api/sugerencias", tags=["sugerencias"])

ESTADOS_VALIDOS = ("revisada", "descartada")


def _out(sugerencia: Sugerencia, autor: str) -> SugerenciaOut:
    return SugerenciaOut(
        id=sugerencia.id,
        usuario_id=sugerencia.usuario_id,
        autor=autor,
        texto=sugerencia.texto,
        estado=sugerencia.estado,
        fecha=sugerencia.created_at.isoformat(),
    )


@router.get("", response_model=list[SugerenciaOut])
def listar_sugerencias(db: DbSession, user: CurrentUser):
    filas = db.execute(
        select(Sugerencia, Usuario.display_name)
        .join(Usuario, Usuario.id == Sugerencia.usuario_id)
        .order_by(Sugerencia.id.desc())
    ).all()
    return [_out(sugerencia, nombre) for sugerencia, nombre in filas]


@router.post("", response_model=SugerenciaOut, status_code=201)
def crear_sugerencia(dto: SugerenciaIn, db: DbSession, user: CurrentUser):
    texto = dto.texto.strip()
    if not texto:
        raise bad_request("El texto es obligatorio")
    nueva = Sugerencia(
        usuario_id=user.id,
        texto=texto,
        estado="pendiente",
        created_at=datetime.now(UTC),
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return _out(nueva, user.display_name)


@router.patch("/{sugerencia_id}", response_model=SugerenciaOut)
def cambiar_estado(
    sugerencia_id: int,
    dto: SugerenciaPatchIn,
    db: DbSession,
    user: CurrentUser,
):
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede cambiar el estado")
    if dto.estado not in ESTADOS_VALIDOS:
        raise bad_request("Estado inválido. Use: revisada, descartada")
    sugerencia = db.get(Sugerencia, sugerencia_id)
    if sugerencia is None:
        raise not_found("Sugerencia no encontrada")
    sugerencia.estado = dto.estado
    db.commit()
    db.refresh(sugerencia)
    autor = db.get(Usuario, sugerencia.usuario_id)
    return _out(sugerencia, autor.display_name if autor else "")
