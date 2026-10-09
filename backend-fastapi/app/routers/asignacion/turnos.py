"""Auxiliar shifts: programmed shifts, shift hours, Saturday rotation, work shifts.

Permissions follow the old RLS policies (99_rls_reference.sql):
- read: fn_puede_ver (every role but invitado). That includes `perfiles`; the
  extra `perfiles_propio` rule (own row) is served by GET /me;
- turnos_programados, rotacion_sabados (gestion = all writes) and horarios_turno
  (update only): fn_puede_gestionar_auxiliares (admin/encargado);
- fn_asignar_turno (perfiles.turno_habitual/sabado_rotativo): the same, checked
  here first so it answers 403 instead of the function's own exception;
- turnos_trabajo create/update: fn_puede_operar (admin/encargado/auxiliar).
Orderings and embeds match the PostgREST queries the Angular app used.
"""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_turnos import (
    AbrirTurnoIn,
    AsignarTurnoIn,
    CerrarTurnoIn,
    HorarioTurnoIn,
    RotacionCreate,
    RotacionUpdate,
    TurnosProgramadosIn,
)
from app.services.asignacion.sql import (
    Permission,
    delete_by_id,
    insert_returning_id,
    not_found,
    require,
    rows,
    update_by_id,
    writing,
)

router = APIRouter()

Rol = Literal["admin", "auxiliar", "decano", "encargado", "invitado", "tecnico"]


def nombre_de(alias: str) -> str:
    """`{nombre_completo}` embed of a perfil joined as `alias` (null when absent)."""
    return (
        f"case when {alias}.id is null then null"
        f" else json_build_object('nombre_completo', {alias}.nombre_completo) end"
    )


def _texto(value: str | None) -> str | None:
    return (value or "").strip() or None


# --- turnos programados ----------------------------------------------------------

_PROGRAMADOS = f"""
    select tp.*, {nombre_de("p")} as perfil
      from horarios.turnos_programados tp
      left join horarios.perfiles p on p.id = tp.perfil_id
"""


@router.get("/turnos-programados")
def listar_turnos_programados(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    sql = text(f"{_PROGRAMADOS} order by tp.desde desc, tp.id desc")
    return [dict(r) for r in rows(db, sql)]


@router.put("/turnos-programados")
def programar_turnos(body: TurnosProgramadosIn, db: AsignacionDb) -> dict:
    """Shifts of several auxiliares from one date (same perfil and date = changed)."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    sql = text(
        """
        insert into horarios.turnos_programados (perfil_id, turno, desde)
        values (:perfil_id, :turno, :desde)
        on conflict (perfil_id, desde) do update set turno = excluded.turno
        """
    )
    with writing(db):
        for fila in body.filas:
            db.execute(
                sql,
                {"perfil_id": fila.perfil_id, "turno": fila.turno, "desde": body.desde},
            )
    return {"guardados": len(body.filas)}


@router.delete("/turnos-programados/{turno_id}", status_code=204)
def eliminar_turno_programado(turno_id: int, db: AsignacionDb) -> Response:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not delete_by_id(db, "turnos_programados", turno_id):
            raise not_found()
    return Response(status_code=204)


@router.get("/turnos/vigente")
def turno_vigente(
    db: AsignacionDb, perfil_id: UUID | None = None, fecha: date | None = None
) -> dict:
    """fn_turno_vigente: latest programmed shift on or before `fecha` (La Paz today)."""
    require(db, Permission.VER)
    sql = text(
        """
        select p.perfil_id, p.fecha, horarios.fn_turno_vigente(p.perfil_id, p.fecha) as turno
          from (select coalesce(cast(:perfil as uuid), horarios.fn_usuario_actual()) as perfil_id,
                       coalesce(cast(:fecha as date),
                                (now() at time zone 'America/La_Paz')::date) as fecha) p
        """
    )
    return dict(rows(db, sql, {"perfil": perfil_id, "fecha": fecha})[0])


# --- horarios de turno -----------------------------------------------------------

_HORARIOS = text(
    "select turno, hora_inicio, hora_fin from horarios.horarios_turno order by hora_inicio"
)


@router.get("/horarios-turno")
def listar_horarios_turno(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [dict(r) for r in rows(db, _HORARIOS)]


@router.put("/horarios-turno")
def guardar_horarios_turno(body: list[HorarioTurnoIn], db: AsignacionDb) -> list[dict]:
    """Change the hours of existing shifts (the four shifts are fixed rows)."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    sql = text(
        "update horarios.horarios_turno set hora_inicio = :hora_inicio,"
        " hora_fin = :hora_fin where turno = :turno"
    )
    with writing(db):
        for h in body:
            db.execute(sql, h.model_dump())
    return [dict(r) for r in rows(db, _HORARIOS)]


# --- perfiles de operación y turno habitual -------------------------------------


@router.get("/auxiliares")
def listar_auxiliares(
    db: AsignacionDb,
    rol: Annotated[list[Rol], Query()] = [],  # noqa: B006 (FastAPI query default)
    activo: bool | None = None,
) -> list[dict]:
    """Perfiles for the operation pages, optionally by rol (repeatable) and activo."""
    require(db, Permission.VER)
    sql = text(
        """
        select id, nombre_completo, correo, rol, activo, turno_habitual,
               sabado_rotativo, creado_en, actualizado_en
          from horarios.perfiles
         where (cardinality(cast(:roles as text[])) = 0 or rol = any(cast(:roles as text[])))
           and (cast(:activo as boolean) is null or activo = cast(:activo as boolean))
         order by nombre_completo
        """
    )
    return [dict(r) for r in rows(db, sql, {"roles": list(rol), "activo": activo})]


@router.put("/auxiliares/{perfil_id}/turno", status_code=204)
def asignar_turno(perfil_id: UUID, body: AsignarTurnoIn, db: AsignacionDb) -> Response:
    """fn_asignar_turno: usual shift and Saturday rotation of a perfil."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    existe = text("select 1 from horarios.perfiles where id = :id")
    if db.execute(existe, {"id": perfil_id}).first() is None:
        raise not_found()
    sql = text(
        "select horarios.fn_asignar_turno(cast(:perfil as uuid), cast(:turno as text),"
        " cast(:sabado as boolean))"
    )
    with writing(db):
        db.execute(
            sql, {"perfil": perfil_id, "turno": body.turno, "sabado": body.sabado}
        )
    return Response(status_code=204)


# --- rotación de sábados ---------------------------------------------------------

_ROTACION = f"""
    select r.*, {nombre_de("p")} as auxiliar
      from horarios.rotacion_sabados r
      left join horarios.perfiles p on p.id = r.auxiliar_id
"""


def _rotacion(db: Session, rotacion_id: int) -> dict:
    found = rows(db, text(f"{_ROTACION} where r.id = :id"), {"id": rotacion_id})
    if not found:
        raise not_found()
    return dict(found[0])


@router.get("/rotacion-sabados")
def listar_rotacion(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [dict(r) for r in rows(db, text(f"{_ROTACION} order by r.fecha desc"))]


@router.post("/rotacion-sabados", status_code=201)
def crear_rotacion(body: RotacionCreate, db: AsignacionDb) -> dict:
    require(db, Permission.GESTIONAR_AUXILIARES)
    values = body.model_dump()
    values["nota"] = _texto(values["nota"])
    with writing(db):
        new_id = insert_returning_id(db, "rotacion_sabados", values)
    return _rotacion(db, new_id)


@router.patch("/rotacion-sabados/{rotacion_id}")
def editar_rotacion(rotacion_id: int, body: RotacionUpdate, db: AsignacionDb) -> dict:
    require(db, Permission.GESTIONAR_AUXILIARES)
    values = body.model_dump(exclude_unset=True)
    if "nota" in values:
        values["nota"] = _texto(values["nota"])
    with writing(db):
        if not update_by_id(db, "rotacion_sabados", rotacion_id, values):
            raise not_found()
    return _rotacion(db, rotacion_id)


@router.delete("/rotacion-sabados/{rotacion_id}", status_code=204)
def eliminar_rotacion(rotacion_id: int, db: AsignacionDb) -> Response:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not delete_by_id(db, "rotacion_sabados", rotacion_id):
            raise not_found()
    return Response(status_code=204)


# --- turnos de trabajo (apertura y cierre) ---------------------------------------

_TRABAJO = f"""
    select t.*, {nombre_de("pa")} as apertura, {nombre_de("pc")} as cierre
      from horarios.turnos_trabajo t
      left join horarios.perfiles pa on pa.id = t.auxiliar_apertura_id
      left join horarios.perfiles pc on pc.id = t.auxiliar_cierre_id
"""


def _trabajo(db: Session, turno_id: int) -> dict:
    found = rows(db, text(f"{_TRABAJO} where t.id = :id"), {"id": turno_id})
    if not found:
        raise not_found()
    return dict(found[0])


@router.get("/turnos-trabajo/estado")
def estado_turno_trabajo(db: AsignacionDb) -> dict:
    """The open work shift (at most one) and the last closed one (shift handover)."""
    require(db, Permission.VER)
    abierto = rows(db, text(f"{_TRABAJO} where t.estado = 'abierto' limit 1"))
    cerrado = rows(
        db,
        text(
            f"{_TRABAJO} where t.estado = 'cerrado'"
            " order by t.cerrado_en desc nulls last limit 1"
        ),
    )
    return {
        "abierto": dict(abierto[0]) if abierto else None,
        "ultimo_cerrado": dict(cerrado[0]) if cerrado else None,
    }


@router.post("/turnos-trabajo", status_code=201)
def abrir_turno_trabajo(body: AbrirTurnoIn, db: AsignacionDb) -> dict:
    """Open a work shift (a second open one fails on the unique index -> 409)."""
    require(db, Permission.OPERAR)
    values = {
        "turno": body.turno,
        "es_sabado_rotativo": body.es_sabado_rotativo,
        "notas_apertura": _texto(body.notas),
    }
    with writing(db):
        new_id = insert_returning_id(db, "turnos_trabajo", values)
    return _trabajo(db, new_id)


@router.post("/turnos-trabajo/{turno_id}/cierre")
def cerrar_turno_trabajo(turno_id: int, body: CerrarTurnoIn, db: AsignacionDb) -> dict:
    """Close a work shift leaving the handover note; the closer is the requester."""
    require(db, Permission.OPERAR)
    sql = text(
        """
        update horarios.turnos_trabajo
           set estado = 'cerrado', cerrado_en = now(),
               auxiliar_cierre_id = horarios.fn_usuario_actual(), notas_cierre = :notas
         where id = :id
        returning 1
        """
    )
    with writing(db):
        if (
            db.execute(sql, {"id": turno_id, "notas": _texto(body.notas)}).first()
            is None
        ):
            raise not_found()
    return _trabajo(db, turno_id)
