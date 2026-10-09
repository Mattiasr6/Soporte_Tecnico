"""Academic scheduling: asignaciones, cesiones, reservas and reubicaciones.

Writes go through the ported SQL RPCs, which hold the business rules and fill
the child tables (horarios, fechas, reubicaciones) in one call:
rpc_guardar_asignacion, rpc_guardar_cesiones, rpc_guardar_reserva and
rpc_reubicar_clase. The anti-clash checks are deferred constraint triggers, so
every write commits inside the request (`writing`) and a clash is answered as
an error, never as a success.

Permissions follow the old RLS policies (99_rls_reference.sql): read =
fn_puede_ver, write/delete = fn_puede_editar on all of these tables. The RPCs
themselves check no role (they relied on RLS), so the API checks first.

List/detail payloads reproduce the PostgREST selects the Angular pages used
(same embed names: docente, materia, carrera, horarios, fechas, receptor,
horario.asignacion, tipo, reubicaciones).
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_horarios import IdOut, LoteOut, RpcPayload
from app.services.asignacion.sql import (
    Permission,
    call_rpc,
    delete_by_id,
    not_found,
    require,
    rows,
    writing,
)

router = APIRouter()

# --- SQL ----------------------------------------------------------------------

_ASIGNACIONES = """
    select a.*,
           json_build_object('id', d.id, 'nombres', d.nombres,
                             'apellidos', d.apellidos) as docente,
           json_build_object('id', m.id, 'nombre', m.nombre) as materia,
           json_build_object('id', c.id, 'nombre', c.nombre, 'sigla', c.sigla,
                             'color', c.color) as carrera,
           coalesce((select json_agg(to_json(h) order by h.dia_semana, h.hora_inicio, h.id)
                       from horarios.asignacion_horarios h
                      where h.asignacion_id = a.id
                        and (cast(:ambiente_id as bigint) is null
                             or h.ambiente_id = :ambiente_id)), '[]'::json) as horarios,
           coalesce((select json_agg(json_build_object('fecha', f.fecha) order by f.fecha)
                       from horarios.asignacion_fechas f
                      where f.asignacion_id = a.id), '[]'::json) as fechas
      from horarios.asignaciones a
      join horarios.docentes d on d.id = a.docente_id
      join horarios.materias m on m.id = a.materia_id
      join horarios.carreras c on c.id = a.carrera_id
"""

_CESIONES = """
    select c.*,
           json_build_object('id', r.id, 'nombres', r.nombres,
                             'apellidos', r.apellidos) as receptor,
           coalesce((select json_agg(json_build_object('fecha', f.fecha) order by f.fecha)
                       from horarios.cesion_fechas f
                      where f.cesion_id = c.id), '[]'::json) as fechas,
           (select to_jsonb(h) || jsonb_build_object('asignacion', jsonb_build_object(
                       'id', a.id, 'grupo', a.grupo, 'docente_id', a.docente_id,
                       'docente', jsonb_build_object('id', d.id, 'nombres', d.nombres,
                                                     'apellidos', d.apellidos),
                       'materia', jsonb_build_object('nombre', m.nombre)))
              from horarios.asignacion_horarios h
              join horarios.asignaciones a on a.id = h.asignacion_id
              join horarios.docentes d on d.id = a.docente_id
              join horarios.materias m on m.id = a.materia_id
             where h.id = c.asignacion_horario_id) as horario
      from horarios.cesiones c
      join horarios.docentes r on r.id = c.docente_receptor_id
"""

_RESERVAS = """
    select r.*, to_json(t) as tipo,
           coalesce((select json_agg(to_json(h) order by h.fecha, h.hora_inicio, h.id)
                       from horarios.reserva_horarios h
                      where h.reserva_id = r.id), '[]'::json) as horarios,
           coalesce((select json_agg(to_json(u) order by u.id)
                       from horarios.reubicaciones u
                      where u.reserva_id = r.id), '[]'::json) as reubicaciones
      from horarios.reservas r
      join horarios.tipos_reserva t on t.id = r.tipo_id
"""


def _asignacion(db: Session, asignacion_id: int) -> dict:
    found = rows(
        db,
        text(f"{_ASIGNACIONES} where a.id = :id"),
        {"id": asignacion_id, "ambiente_id": None},
    )
    if not found:
        raise not_found()
    return dict(found[0])


def _reserva(db: Session, reserva_id: int) -> dict:
    found = rows(db, text(f"{_RESERVAS} where r.id = :id"), {"id": reserva_id})
    if not found:
        raise not_found()
    return dict(found[0])


def _exists(db: Session, table: str, row_id: int) -> None:
    sql = text(f"select 1 from horarios.{table} where id = :id")
    if db.execute(sql, {"id": row_id}).first() is None:
        raise not_found()


def _save(db: Session, function: str, payload: RpcPayload) -> Any:
    """Run a write RPC as an editor and commit (deferred clash checks included)."""
    require(db, Permission.EDITAR)
    with writing(db):
        result = call_rpc(db, function, payload)
    return result


def _delete(db: Session, table: str, row_id: int) -> Response:
    require(db, Permission.EDITAR)
    with writing(db):
        deleted = delete_by_id(db, table, row_id)
    if not deleted:
        raise not_found()
    return Response(status_code=204)


# --- asignaciones -------------------------------------------------------------


@router.get("/asignaciones")
def list_asignaciones(
    db: AsignacionDb, fin_desde: date | None = None, ambiente_id: int | None = None
) -> list[dict]:
    """All asignaciones; `fin_desde` keeps fecha_fin >= that date (the client
    sends its own "today", La Paz time); `ambiente_id`
    keeps those with a horario there and embeds only those horarios."""
    require(db, Permission.VER)
    sql = f"""{_ASIGNACIONES}
        where (cast(:fin_desde as date) is null or a.fecha_fin >= :fin_desde)
          and (cast(:ambiente_id as bigint) is null
               or exists (select 1 from horarios.asignacion_horarios x
                           where x.asignacion_id = a.id and x.ambiente_id = :ambiente_id))
        order by a.id"""
    params = {"fin_desde": fin_desde, "ambiente_id": ambiente_id}
    return [dict(r) for r in rows(db, text(sql), params)]


@router.get("/asignaciones/{asignacion_id}")
def get_asignacion(asignacion_id: int, db: AsignacionDb) -> dict:
    require(db, Permission.VER)
    return _asignacion(db, asignacion_id)


@router.post("/asignaciones", status_code=201)
def create_asignacion(body: RpcPayload, db: AsignacionDb) -> dict:
    payload = {k: v for k, v in body.items() if k != "id"}
    new_id = _save(db, "rpc_guardar_asignacion", payload)
    return _asignacion(db, new_id)


@router.put("/asignaciones/{asignacion_id}")
def update_asignacion(asignacion_id: int, body: RpcPayload, db: AsignacionDb) -> dict:
    require(db, Permission.EDITAR)
    _exists(db, "asignaciones", asignacion_id)
    _save(db, "rpc_guardar_asignacion", {**body, "id": asignacion_id})
    return _asignacion(db, asignacion_id)


@router.delete("/asignaciones/{asignacion_id}", status_code=204)
def delete_asignacion(asignacion_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "asignaciones", asignacion_id)


# --- cesiones (saved in batches: one `lote` = several horarios of a class) ------


@router.get("/cesiones")
def list_cesiones(
    db: AsignacionDb,
    lote: UUID | None = None,
    excluir_lote: UUID | None = None,
    asignacion_horario_id: Annotated[list[int] | None, Query()] = None,
) -> list[dict]:
    require(db, Permission.VER)
    sql = f"""{_CESIONES}
        where (cast(:lote as uuid) is null or c.lote = :lote)
          and (cast(:excluir as uuid) is null or c.lote <> :excluir)
          and (cast(:horarios as bigint[]) is null
               or c.asignacion_horario_id = any(cast(:horarios as bigint[])))
        order by c.id desc"""
    params = {"lote": lote, "excluir": excluir_lote, "horarios": asignacion_horario_id}
    return [dict(r) for r in rows(db, text(sql), params)]


@router.get("/cesiones/{cesion_id}")
def get_cesion(cesion_id: int, db: AsignacionDb) -> dict:
    require(db, Permission.VER)
    found = rows(db, text(f"{_CESIONES} where c.id = :id"), {"id": cesion_id})
    if not found:
        raise not_found()
    return dict(found[0])


@router.post("/cesiones/lotes", response_model=LoteOut, status_code=201)
def create_cesiones(body: RpcPayload, db: AsignacionDb) -> dict:
    payload = {k: v for k, v in body.items() if k != "lote"}
    return {"lote": _save(db, "rpc_guardar_cesiones", payload)}


@router.put("/cesiones/lotes/{lote}", response_model=LoteOut)
def update_cesiones(lote: UUID, body: RpcPayload, db: AsignacionDb) -> dict:
    return {"lote": _save(db, "rpc_guardar_cesiones", {**body, "lote": str(lote)})}


@router.delete("/cesiones/{cesion_id}", status_code=204)
def delete_cesion(cesion_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "cesiones", cesion_id)


# --- reservas (eventos, defensas, mantenimiento) ------------------------------


@router.get("/reservas")
def list_reservas(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [dict(r) for r in rows(db, text(f"{_RESERVAS} order by r.id desc"))]


@router.get("/reservas/{reserva_id}")
def get_reserva(reserva_id: int, db: AsignacionDb) -> dict:
    require(db, Permission.VER)
    return _reserva(db, reserva_id)


@router.post("/reservas", status_code=201)
def create_reserva(body: RpcPayload, db: AsignacionDb) -> dict:
    payload = {k: v for k, v in body.items() if k != "id"}
    return _reserva(db, _save(db, "rpc_guardar_reserva", payload))


@router.put("/reservas/{reserva_id}")
def update_reserva(reserva_id: int, body: RpcPayload, db: AsignacionDb) -> dict:
    require(db, Permission.EDITAR)
    _exists(db, "reservas", reserva_id)
    _save(db, "rpc_guardar_reserva", {**body, "id": reserva_id})
    return _reserva(db, reserva_id)


@router.delete("/reservas/{reserva_id}", status_code=204)
def delete_reserva(reserva_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "reservas", reserva_id)


# --- reubicaciones (move or suspend one class on one date) --------------------


@router.get("/reubicaciones")
def list_reubicaciones(
    db: AsignacionDb,
    asignacion_horario_id: Annotated[list[int] | None, Query()] = None,
) -> list[dict]:
    """Reubicaciones of the given horarios (the form reloads saved destinations)."""
    require(db, Permission.VER)
    sql = text(
        """select u.id, u.asignacion_horario_id, u.fecha, u.ambiente_destino_id,
                  u.aula_destino, u.hora_inicio, u.hora_fin, u.motivo,
                  u.reserva_id, u.cesion_id
             from horarios.reubicaciones u
            where cast(:horarios as bigint[]) is null
               or u.asignacion_horario_id = any(cast(:horarios as bigint[]))
            order by u.fecha, u.id"""
    )
    return [dict(r) for r in rows(db, sql, {"horarios": asignacion_horario_id})]


@router.post("/reubicaciones", response_model=IdOut, status_code=201)
def reubicar_clase(body: RpcPayload, db: AsignacionDb) -> dict:
    """Upsert by (asignacion_horario_id, fecha); no destino = class suspended."""
    return {"id": _save(db, "rpc_reubicar_clase", body)}


@router.delete("/reubicaciones/{reubicacion_id}", status_code=204)
def delete_reubicacion(reubicacion_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "reubicaciones", reubicacion_id)
