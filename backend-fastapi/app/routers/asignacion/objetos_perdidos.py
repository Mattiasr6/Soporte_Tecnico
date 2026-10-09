"""Lost objects (objetos_perdidos) and their photos (old private bucket
`objetos-perdidos`).

Old RLS policies (99_rls_reference.sql and Supabase scripts 25/30), reproduced
with the same SQL helpers:
- read rows and photos: fn_puede_ver;
- create (WITH CHECK) and update (USING and WITH CHECK), upload photos:
  fn_puede_operar — role-only, so one check per request covers both;
- delete rows: fn_puede_gestionar_auxiliares; their photo files go with them;
- delete photo files: gestionar, or operar for files no row references any more
  (exactly the paths fn_limpiar_fotos_objetos returns).
The trigger fn_trg_objeto_perdido keeps the rest: a new object is always
'en_custodia' and found by the requester, the delivery date and who delivered are
set by the DB, and a delivered object can only be changed by admin/encargado.

A photo is mandatory when registering and when delivering, so each is one
multipart request: the server stores the photo, then writes the row; the file is
removed again if the write fails. Photos are served by an authenticated endpoint
(the Angular app fetches them as blobs) instead of signed URLs.
"""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.routers.asignacion.turnos import nombre_de
from app.services.asignacion import fotos
from app.services.asignacion.sql import Permission, not_found, require, rows, writing

router = APIRouter()

CARPETA = fotos.CARPETA_OBJETOS
_OBJETO = f"""
    select o.*,
           case when am.id is null then null
                else json_build_object('codigo', am.codigo, 'color', am.color)
           end as ambiente,
           {nombre_de("en")} as encontro,
           {nombre_de("ep")} as entrego
      from horarios.objetos_perdidos o
      left join horarios.ambientes am on am.id = o.ambiente_id
      left join horarios.perfiles en on en.id = o.encontrado_por
      left join horarios.perfiles ep on ep.id = o.entregado_por
"""


def _texto(value: str | None) -> str | None:
    return (value or "").strip() or None


def _objeto(db: Session, objeto_id: int) -> dict:
    found = rows(db, text(f"{_OBJETO} where o.id = :id"), {"id": objeto_id})
    if not found:
        raise not_found()
    return dict(found[0])


def _guardar_foto(foto: UploadFile, prefijo: str) -> str:
    contenido = foto.file.read(fotos.MAX_BYTES + 1)
    return fotos.guardar(foto.content_type, contenido, CARPETA, prefijo)


@router.get("/objetos-perdidos")
def listar_objetos(
    db: AsignacionDb, limite: Annotated[int, Query(ge=1, le=1000)] = 300
) -> list[dict]:
    """Latest lost objects (by found date, newest first)."""
    require(db, Permission.VER)
    sql = text(f"{_OBJETO} order by o.encontrado_en desc, o.id desc limit :limite")
    return [dict(r) for r in rows(db, sql, {"limite": limite})]


@router.post("/objetos-perdidos", status_code=201)
def registrar_objeto(
    db: AsignacionDb,
    nombre: Annotated[str, Form()],
    ambiente_id: Annotated[int, Form()],
    foto: Annotated[UploadFile, File()],
    descripcion: Annotated[str | None, Form()] = None,
    encontrado_en: Annotated[datetime | None, Form()] = None,
) -> dict:
    """Register a found object with its (mandatory) photo; multipart."""
    require(db, Permission.OPERAR)
    ruta = _guardar_foto(foto, "objetos")
    sql = text(
        """
        insert into horarios.objetos_perdidos
               (nombre, descripcion, ambiente_id, encontrado_en, foto_path)
        values (:nombre, :descripcion, :ambiente_id,
                coalesce(cast(:encontrado_en as timestamptz), now()), :foto_path)
        returning id
        """
    )
    try:
        with writing(db):
            objeto_id = db.execute(
                sql,
                {
                    "nombre": nombre.strip(),
                    "descripcion": _texto(descripcion),
                    "ambiente_id": ambiente_id,
                    "encontrado_en": encontrado_en,
                    "foto_path": ruta,
                },
            ).scalar_one()
    except BaseException:
        fotos.borrar([ruta], CARPETA)
        raise
    return _objeto(db, objeto_id)


@router.post("/objetos-perdidos/{objeto_id}/entrega")
def entregar_objeto(
    objeto_id: int,
    db: AsignacionDb,
    entregado_a: Annotated[str, Form()],
    foto: Annotated[UploadFile, File()],
    entregado_documento: Annotated[str | None, Form()] = None,
    observacion_entrega: Annotated[str | None, Form()] = None,
) -> dict:
    """Deliver an object to its owner with the (mandatory) delivery photo."""
    require(db, Permission.OPERAR)
    existe = text("select 1 from horarios.objetos_perdidos where id = :id")
    if db.execute(existe, {"id": objeto_id}).first() is None:
        raise not_found()
    ruta = _guardar_foto(foto, "entregas")
    sql = text(
        """
        update horarios.objetos_perdidos n
           set estado = 'entregado', entregado_a = :a, entregado_documento = :doc,
               observacion_entrega = :obs, foto_entrega_path = :ruta
          from horarios.objetos_perdidos o
         where n.id = :id and o.id = n.id
        returning o.foto_entrega_path as anterior
        """
    )
    params = {
        "id": objeto_id,
        "a": _texto(entregado_a),
        "doc": _texto(entregado_documento),
        "obs": _texto(observacion_entrega),
        "ruta": ruta,
    }
    try:
        with writing(db):
            anterior = db.execute(sql, params).scalar_one()
    except BaseException:
        fotos.borrar([ruta], CARPETA)
        raise
    if anterior and anterior != ruta:
        fotos.borrar([anterior], CARPETA)
    return _objeto(db, objeto_id)


@router.delete("/objetos-perdidos/{objeto_id}", status_code=204)
def eliminar_objeto(objeto_id: int, db: AsignacionDb) -> Response:
    require(db, Permission.GESTIONAR_AUXILIARES)
    sql = text(
        "delete from horarios.objetos_perdidos where id = :id"
        " returning foto_path, foto_entrega_path"
    )
    with writing(db):
        fila = db.execute(sql, {"id": objeto_id}).first()
    if fila is None:
        raise not_found()
    fotos.borrar(list(fila), CARPETA)
    return Response(status_code=204)


@router.post("/objetos-perdidos/fotos/limpiar")
def limpiar_fotos(db: AsignacionDb) -> dict:
    """fn_limpiar_fotos_objetos: drop photos older than 9 months (the record
    stays) and delete their files."""
    require(db, Permission.OPERAR)
    with writing(db):
        rutas = list(
            db.execute(
                text("select * from horarios.fn_limpiar_fotos_objetos()")
            ).scalars()
        )
    fotos.borrar(rutas, CARPETA)
    return {"eliminadas": len(rutas)}


@router.get("/objetos-perdidos/{objeto_id}/fotos/{tipo}")
def ver_foto(
    objeto_id: int, tipo: Literal["objeto", "entrega"], db: AsignacionDb
) -> FileResponse:
    require(db, Permission.VER)
    columna = "foto_path" if tipo == "objeto" else "foto_entrega_path"
    sql = text(f"select {columna} from horarios.objetos_perdidos where id = :id")
    return fotos.servir(db.execute(sql, {"id": objeto_id}).scalar(), CARPETA)
