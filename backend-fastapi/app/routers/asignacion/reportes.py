"""Shift reports (reportes_turno), their pending tasks and the closing photo.

Old RLS policies (99_rls_reference.sql), reproduced here with the same SQL helpers:
- read reportes_turno / reporte_tareas: fn_puede_ver;
- create report: fn_puede_operar() and (auxiliar_id = me or
  fn_puede_gestionar_auxiliares()) and fn_puede_cerrar_turno(turno);
- update/delete report (USING and WITH CHECK): fn_puede_operar() and
  (fn_puede_gestionar_auxiliares() or (auxiliar_id = me and fecha = today in
  America/La_Paz and fn_puede_cerrar_turno(turno))) — exactly
  fn_puede_editar_reporte(id), evaluated before the write and again on the
  written row (WITH CHECK) before the commit;
- create/delete tasks: fn_puede_editar_reporte(reporte_id); mark a task done
  (update): fn_puede_operar.
The photo (old private bucket `reportes-turno`) follows its report: upload and
delete need fn_puede_editar_reporte, download needs fn_puede_ver. It is served by
an authenticated endpoint (the Angular app fetches it as a blob with its Bearer
token) instead of signed URLs. Triggers keep the rest (expiry at next noon,
done tasks are fixed, reports with done tasks cannot be deleted).
"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.routers.asignacion.turnos import nombre_de
from app.schemas.asignacion_turnos import (
    ReporteCreate,
    ReporteUpdate,
    TareaEdicion,
    TareaMarca,
    TareaNueva,
)
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

# A task with its `ambiente{codigo}` and `ejecutor{nombre_completo}` embeds.
_TAREA = f"""
    select t.*,
           case when am.id is null then null
                else json_build_object('codigo', am.codigo) end as ambiente,
           {nombre_de("ej")} as ejecutor
      from horarios.reporte_tareas t
      left join horarios.ambientes am on am.id = t.ambiente_id
      left join horarios.perfiles ej on ej.id = t.hecha_por
"""
_REPORTE = f"""
    select r.*, {nombre_de("au")} as autor,
           coalesce((select json_agg(to_json(x) order by x.id)
                       from ({_TAREA} where t.reporte_id = r.id) x), '[]'::json) as tareas
      from horarios.reportes_turno r
      left join horarios.perfiles au on au.id = r.auxiliar_id
"""
_PUEDE_EDITAR = text("select horarios.fn_puede_editar_reporte(:id)")
_PUEDE_CREAR = text(
    """
    select horarios.fn_puede_operar()
       and (coalesce(cast(:aux as uuid), horarios.fn_usuario_actual())
              = horarios.fn_usuario_actual()
            or horarios.fn_puede_gestionar_auxiliares())
       and horarios.fn_puede_cerrar_turno(:turno)
    """
)
_MEDIA_TYPES = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _forbidden() -> HTTPException:
    return HTTPException(403, error_detail(FORBIDDEN_MESSAGE, "42501"))


def _texto(value: str | None) -> str | None:
    return (value or "").strip() or None


def _reporte(db: Session, reporte_id: int) -> dict:
    found = rows(db, text(f"{_REPORTE} where r.id = :id"), {"id": reporte_id})
    if not found:
        raise not_found()
    return dict(found[0])


def _tareas(db: Session, reporte_id: int) -> list[dict]:
    sql = text(f"{_TAREA} where t.reporte_id = :id order by t.id")
    return [dict(r) for r in rows(db, sql, {"id": reporte_id})]


def _require_editable(db: Session, reporte_id: int) -> None:
    """404 if the report does not exist, 403 unless fn_puede_editar_reporte."""
    existe = text("select 1 from horarios.reportes_turno where id = :id")
    if db.execute(existe, {"id": reporte_id}).first() is None:
        raise not_found()
    if not db.execute(_PUEDE_EDITAR, {"id": reporte_id}).scalar():
        raise _forbidden()


def _insert_tareas(db: Session, reporte_id: int, tareas: list[TareaNueva]) -> None:
    sql = text(
        "insert into horarios.reporte_tareas (reporte_id, descripcion, ambiente_id)"
        " values (:reporte_id, :descripcion, :ambiente_id)"
    )
    for t in tareas:
        db.execute(
            sql,
            {
                "reporte_id": reporte_id,
                "descripcion": t.descripcion,
                "ambiente_id": t.ambiente_id,
            },
        )


# --- reportes --------------------------------------------------------------------


@router.get("/reportes-turno")
def listar_reportes(
    db: AsignacionDb, limite: Annotated[int, Query(ge=1, le=200)] = 15
) -> list[dict]:
    """Latest shift reports with their tasks (newest first)."""
    require(db, Permission.VER)
    sql = text(f"{_REPORTE} order by r.creado_en desc limit :limite")
    return [dict(r) for r in rows(db, sql, {"limite": limite})]


@router.post("/reportes-turno", status_code=201)
def crear_reporte(body: ReporteCreate, db: AsignacionDb) -> dict:
    """A shift report and its pending tasks, in one transaction."""
    params = {"aux": body.auxiliar_id, "turno": body.turno}
    if not db.execute(_PUEDE_CREAR, params).scalar():
        raise _forbidden()
    sql = text(
        """
        insert into horarios.reportes_turno (turno, novedades, auxiliar_id)
        values (:turno, :novedades,
                coalesce(cast(:aux as uuid), horarios.fn_usuario_actual()))
        returning id
        """
    )
    with writing(db):
        reporte_id = db.execute(
            sql, {**params, "novedades": _texto(body.novedades)}
        ).scalar_one()
        if body.tareas:
            if not db.execute(_PUEDE_EDITAR, {"id": reporte_id}).scalar():
                db.rollback()
                raise _forbidden()
            _insert_tareas(db, reporte_id, body.tareas)
    return _reporte(db, reporte_id)


@router.patch("/reportes-turno/{reporte_id}")
def editar_reporte(reporte_id: int, body: ReporteUpdate, db: AsignacionDb) -> dict:
    _require_editable(db, reporte_id)
    sql = text(
        "update horarios.reportes_turno set turno = :turno, novedades = :novedades"
        " where id = :id"
    )
    with writing(db):
        db.execute(
            sql,
            {
                "id": reporte_id,
                "turno": body.turno,
                "novedades": _texto(body.novedades),
            },
        )
        # WITH CHECK: the written row must still be editable by the requester.
        if not db.execute(_PUEDE_EDITAR, {"id": reporte_id}).scalar():
            db.rollback()
            raise _forbidden()
    return _reporte(db, reporte_id)


@router.delete("/reportes-turno/{reporte_id}", status_code=204)
def eliminar_reporte(reporte_id: int, db: AsignacionDb) -> Response:
    _require_editable(db, reporte_id)
    sql = text("delete from horarios.reportes_turno where id = :id returning foto_path")
    with writing(db):
        foto_path = db.execute(sql, {"id": reporte_id}).scalar_one()
    fotos.borrar([foto_path])
    return Response(status_code=204)


# --- tareas ----------------------------------------------------------------------


@router.put("/reportes-turno/{reporte_id}/tareas")
def reemplazar_tareas(
    reporte_id: int, body: list[TareaEdicion], db: AsignacionDb
) -> list[dict]:
    """Edit the report's pending tasks: change listed ones, add new ones (no id)
    and remove pending ones left out. Done tasks are never touched."""
    _require_editable(db, reporte_id)
    pendientes = {
        r["id"]: r
        for r in rows(
            db,
            text(
                "select id, descripcion, ambiente_id from horarios.reporte_tareas"
                " where reporte_id = :id and not hecha"
            ),
            {"id": reporte_id},
        )
    }
    quedan = {t.id for t in body if t.id is not None}
    if not quedan <= pendientes.keys():
        raise HTTPException(
            422,
            error_detail(
                "Una de las tareas no es una tarea pendiente de este reporte.", None
            ),
        )
    borrar = [tid for tid in pendientes if tid not in quedan]
    with writing(db):
        if borrar:
            db.execute(
                text("delete from horarios.reporte_tareas where id = any(:ids)"),
                {"ids": borrar},
            )
        for t in body:
            antes = pendientes.get(t.id) if t.id is not None else None
            if antes and (antes["descripcion"], antes["ambiente_id"]) != (
                t.descripcion,
                t.ambiente_id,
            ):
                db.execute(
                    text(
                        "update horarios.reporte_tareas set descripcion = :d,"
                        " ambiente_id = :a where id = :id"
                    ),
                    {"id": t.id, "d": t.descripcion, "a": t.ambiente_id},
                )
        _insert_tareas(db, reporte_id, [t for t in body if t.id is None])
    return _tareas(db, reporte_id)


@router.get("/reporte-tareas/pendientes")
def tareas_pendientes(db: AsignacionDb) -> list[dict]:
    """Tasks no shift marked done yet (oldest first), with their report."""
    require(db, Permission.VER)
    sql = text(
        f"""
        select x.*,
               json_build_object('turno', r.turno, 'fecha', r.fecha,
                                 'autor', {nombre_de("au")}) as reporte
          from ({_TAREA} where not t.hecha) x
          join horarios.reportes_turno r on r.id = x.reporte_id
          left join horarios.perfiles au on au.id = r.auxiliar_id
         order by x.creado_en, x.id
        """
    )
    return [dict(r) for r in rows(db, sql)]


@router.patch("/reporte-tareas/{tarea_id}")
def marcar_tarea(tarea_id: int, body: TareaMarca, db: AsignacionDb) -> dict:
    """Mark (or unmark) a task done; the requester is recorded as who did it."""
    require(db, Permission.OPERAR)
    sql = text(
        """
        update horarios.reporte_tareas
           set hecha = :hecha,
               hecha_por = case when :hecha then horarios.fn_usuario_actual() end,
               hecha_en = case when :hecha then now() end
         where id = :id
        returning *
        """
    )
    with writing(db):
        found = (
            db.execute(sql, {"id": tarea_id, "hecha": body.hecha}).mappings().first()
        )
        if found is None:
            raise not_found()
        tarea = dict(found)
    return tarea


# --- foto del cierre -------------------------------------------------------------


@router.post("/reportes-turno/fotos/limpiar")
def limpiar_fotos(db: AsignacionDb) -> dict:
    """fn_limpiar_fotos_reporte: clear expired photos (after noon) and delete their files."""
    require(db, Permission.OPERAR)
    with writing(db):
        rutas = list(
            db.execute(
                text("select * from horarios.fn_limpiar_fotos_reporte()")
            ).scalars()
        )
    fotos.borrar(rutas)
    return {"eliminadas": len(rutas)}


@router.post("/reportes-turno/{reporte_id}/foto")
def subir_foto(
    reporte_id: int, foto: Annotated[UploadFile, File()], db: AsignacionDb
) -> dict:
    """Store (or replace) the closing photo of a report; multipart field `foto`."""
    _require_editable(db, reporte_id)
    nueva = fotos.guardar(foto.content_type, foto.file.read(fotos.MAX_BYTES + 1))
    sql = text(
        """
        update horarios.reportes_turno n set foto_path = :ruta
          from horarios.reportes_turno o
         where n.id = :id and o.id = n.id
        returning o.foto_path as anterior, n.foto_path, n.foto_expira
        """
    )
    try:
        with writing(db):
            fila = db.execute(sql, {"id": reporte_id, "ruta": nueva}).mappings().one()
    except BaseException:
        fotos.borrar([nueva])
        raise
    if fila["anterior"] != nueva:
        fotos.borrar([fila["anterior"]])
    return {
        "id": reporte_id,
        "foto_path": fila["foto_path"],
        "foto_expira": fila["foto_expira"],
    }


@router.get("/reportes-turno/{reporte_id}/foto")
def ver_foto(reporte_id: int, db: AsignacionDb) -> FileResponse:
    require(db, Permission.VER)
    sql = text("select foto_path from horarios.reportes_turno where id = :id")
    relativo = db.execute(sql, {"id": reporte_id}).scalar()
    path = fotos.resolve(relativo) if relativo else None
    if path is None or not path.is_file():
        raise not_found()
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
        headers={"Cache-Control": "private, no-store"},
    )


@router.delete("/reportes-turno/{reporte_id}/foto", status_code=204)
def eliminar_foto(reporte_id: int, db: AsignacionDb) -> Response:
    _require_editable(db, reporte_id)
    sql = text(
        """
        update horarios.reportes_turno n set foto_path = null
          from horarios.reportes_turno o
         where n.id = :id and o.id = n.id
        returning o.foto_path as anterior
        """
    )
    with writing(db):
        anterior = db.execute(sql, {"id": reporte_id}).scalar_one()
    fotos.borrar([anterior])
    return Response(status_code=204)
