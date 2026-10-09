"""Read-only occupancy and clash queries (ported SQL functions in `horarios`).

fn_ocupaciones, fn_conflictos, fn_verificar_choques, fn_ambientes_libres,
fn_ambientes_libres_fechas and fn_estado_ambientes are STABLE functions that
read the scheduling tables; with Supabase they ran under those tables' RLS,
whose read rule was fn_puede_ver, so every endpoint here requires it.

Queries that take a JSON "ignorar"/"items" argument are POST endpoints with a
typed body; they never write. Rows keep the functions' own order.
"""

import json
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_horarios import (
    AmbientesLibresFechasIn,
    AmbientesLibresIn,
    VerificarChoquesIn,
)
from app.services.asignacion.sql import Permission, require, rows

router = APIRouter()


def _jsonb(value: BaseModel | list[BaseModel]) -> str:
    """Serialize a body part for a `jsonb` argument, leaving out unset keys."""
    if isinstance(value, list):
        return json.dumps([v.model_dump(mode="json", exclude_none=True) for v in value])
    return json.dumps(value.model_dump(mode="json", exclude_none=True))


@router.get("/ocupaciones")
def ocupaciones(
    desde: date,
    hasta: date,
    db: AsignacionDb,
    ignorar_reserva_id: int | None = None,
    ignorar_cesion_id: int | None = None,
) -> list[dict]:
    """Everything occupying an ambiente between two dates (classes, cesiones, reservas)."""
    require(db, Permission.VER)
    sql = text(
        "select * from horarios.fn_ocupaciones(cast(:desde as date), cast(:hasta as date),"
        " cast(:reserva as bigint), cast(:cesion as bigint))"
    )
    params = {
        "desde": desde,
        "hasta": hasta,
        "reserva": ignorar_reserva_id,
        "cesion": ignorar_cesion_id,
    }
    return [dict(r) for r in rows(db, sql, params)]


@router.get("/conflictos")
def conflictos(desde: date, hasta: date, db: AsignacionDb) -> list[dict]:
    """Existing clashes in a date range."""
    require(db, Permission.VER)
    sql = text(
        "select * from horarios.fn_conflictos(cast(:desde as date), cast(:hasta as date))"
    )
    return [dict(r) for r in rows(db, sql, {"desde": desde, "hasta": hasta})]


@router.post("/choques/verificar")
def verificar_choques(body: VerificarChoquesIn, db: AsignacionDb) -> list[dict]:
    """Clashes the candidate items would cause (live validation before saving)."""
    require(db, Permission.VER)
    if not body.items:
        return []
    sql = text(
        "select * from horarios.fn_verificar_choques(cast(:items as jsonb),"
        " cast(:ignorar as jsonb))"
    )
    params = {"items": _jsonb(body.items), "ignorar": _jsonb(body.ignorar)}
    return [dict(r) for r in rows(db, sql, params)]


@router.post("/ambientes-libres")
def ambientes_libres(body: AmbientesLibresIn, db: AsignacionDb) -> list[dict]:
    """Ambientes free on one date and time range."""
    require(db, Permission.VER)
    sql = text(
        "select * from horarios.fn_ambientes_libres(cast(:fecha as date),"
        " cast(:hi as time), cast(:hf as time), cast(:tipo as text),"
        " cast(:ignorar as jsonb))"
    )
    params = {
        "fecha": body.fecha,
        "hi": body.hora_inicio,
        "hf": body.hora_fin,
        "tipo": body.tipo,
        "ignorar": _jsonb(body.ignorar),
    }
    return [dict(r) for r in rows(db, sql, params)]


@router.post("/ambientes-libres/fechas")
def ambientes_libres_fechas(
    body: AmbientesLibresFechasIn, db: AsignacionDb
) -> list[dict]:
    """Ambientes free on ALL the given dates in the time range."""
    require(db, Permission.VER)
    if not body.fechas:
        return []
    sql = text(
        "select * from horarios.fn_ambientes_libres_fechas(cast(:fechas as date[]),"
        " cast(:hi as time), cast(:hf as time), cast(:tipo as text),"
        " cast(:ignorar as jsonb))"
    )
    params = {
        "fechas": body.fechas,
        "hi": body.hora_inicio,
        "hf": body.hora_fin,
        "tipo": body.tipo,
        "ignorar": _jsonb(body.ignorar),
    }
    return [dict(r) for r in rows(db, sql, params)]


@router.get("/estado-ambientes")
def estado_ambientes(db: AsignacionDb) -> list[dict]:
    """Free/occupied state of every ambiente right now (America/La_Paz)."""
    require(db, Permission.VER)
    return [
        dict(r) for r in rows(db, text("select * from horarios.fn_estado_ambientes()"))
    ]
