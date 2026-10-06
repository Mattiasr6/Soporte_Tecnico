"""Novedades: muro de turno para auxiliares (novedades, objetos, cierres)."""

import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.laboratorio import Laboratorio
from app.models.novedad import Novedad
from app.routers.laboratorios import TURNOS, _gestiona_equipo
from app.schemas.novedad import NovedadAccion, NovedadOut

router = APIRouter(prefix="/api/novedades", tags=["novedades"])

TIPOS: tuple[str, ...] = ("novedad", "objeto", "cierre")
ESTADO_INICIAL = {"novedad": "publicado", "objeto": "pendiente", "cierre": "pendiente"}

_FOTOS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "aux_reportes"
_MAX_FOTO = 5 * 1024 * 1024
_FOTO_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _norm(s: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFD", (s or "").strip().casefold())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _estado_efectivo(novedad: Novedad, hoy: date) -> str:
    if (
        novedad.tipo == "objeto"
        and novedad.estado == "pendiente"
        and (hoy - novedad.fecha_registro).days > 90
    ):
        return "vencido"
    return novedad.estado


def _serializar(db: DbSession, rows: list[Novedad]) -> list[dict[str, object]]:
    hoy = datetime.now(UTC).date()
    lids = {r.laboratorio_id for r in rows if r.laboratorio_id is not None}
    nombres = (
        {
            lab.id: lab.nombre
            for lab in db.scalars(
                select(Laboratorio).where(Laboratorio.id.in_(lids or [-1]))
            ).all()
        }
        if lids
        else {}
    )
    return [
        {
            "id": r.id,
            "usuario_id": r.usuario_id,
            "auxiliar_nombre": r.auxiliar_nombre,
            "tipo": r.tipo,
            "texto": r.texto,
            "turno": r.turno,
            "laboratorio_id": r.laboratorio_id,
            "laboratorio": nombres.get(r.laboratorio_id or -1, ""),
            "tiene_foto": bool(r.foto_path),
            "estado": _estado_efectivo(r, hoy),
            "fecha_registro": r.fecha_registro,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def _guardar_foto(foto: UploadFile, contenido: bytes) -> str:
    ext = _FOTO_EXT.get((foto.content_type or "").lower())
    if ext is None:
        raise bad_request("Foto debe ser JPG, PNG o WEBP")
    if not contenido or len(contenido) > _MAX_FOTO:
        raise bad_request("Foto vacia o mayor a 5MB")
    carpeta = _FOTOS_DIR / datetime.now(UTC).strftime("%Y-%m")
    carpeta.mkdir(parents=True, exist_ok=True)
    relativo = f"{carpeta.name}/{uuid.uuid4().hex}.{ext}"
    (_FOTOS_DIR / relativo).write_bytes(contenido)
    return relativo


@router.get("", response_model=list[NovedadOut])
def listar(
    db: DbSession,
    user: CurrentUser,
    tipo: str | None = None,
    estado: str | None = None,
) -> Any:
    del user
    q = select(Novedad).order_by(Novedad.fecha_registro.desc(), Novedad.id.desc())
    if tipo is not None:
        if tipo not in TIPOS:
            raise bad_request("tipo debe ser novedad, objeto o cierre")
        q = q.where(Novedad.tipo == tipo)
    filas = list(db.scalars(q).all())
    salida = _serializar(db, filas)
    if estado is not None:
        salida = [r for r in salida if r["estado"] == estado]
    return salida


@router.post("", response_model=NovedadOut, status_code=201)
async def crear(
    db: DbSession,
    user: CurrentUser,
    tipo: Annotated[str | None, Form()] = None,
    texto: Annotated[str | None, Form()] = None,
    auxiliar_nombre: Annotated[str | None, Form()] = None,
    turno: Annotated[str | None, Form()] = None,
    laboratorio_id: Annotated[int | None, Form()] = None,
    foto: Annotated[UploadFile | None, File()] = None,
) -> Any:
    tipo = (tipo or "").strip()
    texto = (texto or "").strip()
    auxiliar_nombre = (auxiliar_nombre or "").strip()
    if tipo not in TIPOS:
        raise bad_request("tipo debe ser novedad, objeto o cierre")
    if not texto or len(texto) > 2000:
        raise bad_request("Texto obligatorio (maximo 2000 caracteres)")
    if not auxiliar_nombre:
        raise bad_request("Falta quien reporta (soy)")
    turno_val = None
    if turno is not None and str(turno).strip():
        if str(turno).strip() not in TURNOS:
            raise bad_request(f"Turno debe ser uno de: {', '.join(TURNOS)}")
        turno_val = str(turno).strip()
    lab = None
    if laboratorio_id is not None:
        lab = db.get(Laboratorio, laboratorio_id)
        if lab is None:
            raise bad_request("Laboratorio no existe")
    foto_path = None
    if foto is not None and (foto.filename or "").strip():
        foto_path = _guardar_foto(foto, await foto.read())
    if tipo == "cierre" and not foto_path:
        raise bad_request("El cierre de turno exige foto de las llaves")
    now = datetime.now(UTC)
    fila = Novedad(
        usuario_id=user.id,
        auxiliar_nombre=auxiliar_nombre,
        tipo=tipo,
        texto=texto,
        turno=turno_val,
        laboratorio_id=lab.id if lab is not None else None,
        foto_path=foto_path,
        estado=ESTADO_INICIAL[tipo],
        fecha_registro=now.date(),
        created_at=now,
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return _serializar(db, [fila])[0]


@router.patch("/{novedad_id}", response_model=NovedadOut)
def accionar(
    novedad_id: int, dto: NovedadAccion, db: DbSession, user: CurrentUser
) -> Any:
    fila = db.get(Novedad, novedad_id)
    if fila is None:
        raise not_found("Novedad no encontrada")
    accion = (dto.accion or "").strip()
    hoy = datetime.now(UTC).date()
    if accion == "devolver":
        if fila.tipo != "objeto" or _estado_efectivo(fila, hoy) != "pendiente":
            raise bad_request("Solo se puede devolver un objeto pendiente")
        es_gestion = True
        try:
            _gestiona_equipo(user)
        except HTTPException:
            es_gestion = False
        if not es_gestion and _norm(dto.auxiliar_nombre or "") != _norm(
            fila.auxiliar_nombre
        ):
            raise bad_request("Solo el reportante o un encargado puede devolver")
        fila.estado = "devuelto"
    elif accion in ("validar", "rechazar"):
        if fila.tipo != "cierre" or fila.estado != "pendiente":
            raise bad_request("Solo se valida un cierre pendiente")
        _gestiona_equipo(user)
        fila.estado = "validado" if accion == "validar" else "rechazado"
    else:
        raise bad_request("accion debe ser devolver, validar o rechazar")
    db.commit()
    db.refresh(fila)
    return _serializar(db, [fila])[0]


@router.get("/{novedad_id}/foto")
def ver_foto(novedad_id: int, db: DbSession, user: CurrentUser) -> FileResponse:
    del user
    fila = db.get(Novedad, novedad_id)
    if fila is None or not fila.foto_path:
        raise not_found("Sin foto")
    ruta = _FOTOS_DIR / fila.foto_path
    if not ruta.is_file():
        raise not_found("Sin foto")
    return FileResponse(ruta)


@router.post("/purga")
def purgar(db: DbSession, user: CurrentUser) -> dict[str, int]:
    _gestiona_equipo(user)
    hoy = datetime.now(UTC).date()
    viejos = [
        r
        for r in db.scalars(select(Novedad).where(Novedad.tipo == "objeto")).all()
        if _estado_efectivo(r, hoy) == "vencido"
    ]
    for r in viejos:
        if r.foto_path:
            (_FOTOS_DIR / r.foto_path).unlink(missing_ok=True)
        db.delete(r)
    db.commit()
    return {"eliminados": len(viejos)}
