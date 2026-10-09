"""Lab novedades: free-text notices of a shift with an optional photo.

Ported from Django `novedades_vista` (tab "novedades", Soporte table
`Novedades`) onto `horarios.novedades` (migration 0025, which explains why it is
not part of `reportes_turno`). Listed for NOVEDADES_VIGENCIA_DIAS La Paz calendar
days, newest first, filtered by turno (M/MD/T/N) and lab.

Permissions (same SQL helpers as the rest of the module):
- read and photo download: fn_puede_ver;
- create: fn_puede_operar (admin, encargado, auxiliar, tecnico);
- delete: the author or fn_puede_gestionar_auxiliares.
The photo is stored with `app.services.asignacion.fotos` (folder `novedades`)
and served by an authenticated endpoint, like the shift-report photo.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.db.asignacion import AsignacionDb
from app.routers.asignacion.turnos import nombre_de
from app.schemas.asignacion_turnos import TurnoCodigo
from app.services.asignacion import fotos
from app.services.asignacion.sql import (
    FORBIDDEN_MESSAGE,
    Permission,
    error_detail,
    not_found,
    require,
    rows,
    writing,
)

router = APIRouter()

# Django NOV_VIGENCIA_DIAS: today and the 3 previous calendar days.
NOVEDADES_VIGENCIA_DIAS = 3
CARPETA = "novedades"
MAX_TEXTO = 2000

_NOVEDAD = f"""
    select n.*, {nombre_de("au")} as autor,
           case when am.id is null then null
                else json_build_object('codigo', am.codigo, 'nombre', am.nombre,
                                       'color', am.color) end as ambiente
      from horarios.novedades n
      left join horarios.perfiles au on au.id = n.autor_id
      left join horarios.ambientes am on am.id = n.ambiente_id
"""
_PUEDE_BORRAR = text(
    """
    select horarios.fn_puede_operar()
       and (horarios.fn_puede_gestionar_auxiliares()
            or n.autor_id = horarios.fn_usuario_actual())
      from horarios.novedades n where n.id = :id
    """
)


def _novedad(db: AsignacionDb, novedad_id: int) -> dict:
    found = rows(db, text(f"{_NOVEDAD} where n.id = :id"), {"id": novedad_id})
    if not found:
        raise not_found()
    return dict(found[0])


@router.get("/novedades")
def listar_novedades(
    db: AsignacionDb,
    turno: TurnoCodigo | None = None,
    ambiente_id: int | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[dict]:
    """Novedades of the last NOVEDADES_VIGENCIA_DIAS days, newest first."""
    require(db, Permission.VER)
    sql = text(
        f"""
        {_NOVEDAD}
         where n.fecha >= (now() at time zone 'America/La_Paz')::date - :dias
           and (cast(:turno as text) is null or n.turno = :turno)
           and (cast(:amb as bigint) is null or n.ambiente_id = :amb)
         order by n.creado_en desc, n.id desc
         limit :limite
        """
    )
    params = {
        "dias": NOVEDADES_VIGENCIA_DIAS,
        "turno": turno,
        "amb": ambiente_id,
        "limite": limite,
    }
    return [dict(r) for r in rows(db, sql, params)]


@router.post("/novedades", status_code=201)
def crear_novedad(
    db: AsignacionDb,
    texto: Annotated[str, Form()],
    turno: Annotated[TurnoCodigo | None, Form()] = None,
    ambiente_id: Annotated[int | None, Form()] = None,
    foto: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """A novedad (multipart: texto, turno?, ambiente_id?, foto?) in one request."""
    require(db, Permission.OPERAR)
    texto = texto.strip()
    if not texto or len(texto) > MAX_TEXTO:
        raise HTTPException(
            422,
            error_detail("El texto es obligatorio (máximo 2000 caracteres).", None),
        )
    ruta = None
    if foto is not None and (foto.filename or "").strip():
        ruta = fotos.guardar(
            foto.content_type, foto.file.read(fotos.MAX_BYTES + 1), CARPETA
        )
    sql = text(
        """
        insert into horarios.novedades (turno, ambiente_id, texto, foto_path)
        values (coalesce(cast(:turno as text), horarios.fn_turno_horario_de(now())),
                :amb, :texto, :ruta)
        returning id
        """
    )
    try:
        with writing(db):
            novedad_id = db.execute(
                sql,
                {"turno": turno, "amb": ambiente_id, "texto": texto, "ruta": ruta},
            ).scalar_one()
    except BaseException:
        fotos.borrar([ruta], CARPETA)
        raise
    return _novedad(db, novedad_id)


@router.delete("/novedades/{novedad_id}", status_code=204)
def eliminar_novedad(novedad_id: int, db: AsignacionDb) -> Response:
    puede = db.execute(_PUEDE_BORRAR, {"id": novedad_id}).first()
    if puede is None:
        raise not_found()
    if not puede[0]:
        raise HTTPException(403, error_detail(FORBIDDEN_MESSAGE, "42501"))
    sql = text("delete from horarios.novedades where id = :id returning foto_path")
    with writing(db):
        ruta = db.execute(sql, {"id": novedad_id}).scalar_one()
    fotos.borrar([ruta], CARPETA)
    return Response(status_code=204)


@router.get("/novedades/{novedad_id}/foto")
def ver_foto_novedad(novedad_id: int, db: AsignacionDb) -> FileResponse:
    require(db, Permission.VER)
    sql = text("select foto_path from horarios.novedades where id = :id")
    return fotos.servir(db.execute(sql, {"id": novedad_id}).scalar(), CARPETA)
