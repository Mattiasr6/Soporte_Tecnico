"""Auxiliar operation: tickets (atenciones), repair forms, PC states and baja requests.

Old RLS policies (99_rls_reference.sql), reproduced with the same SQL helpers:
- read atenciones, fallas_pc, solicitudes_baja, ambiente_pcs: fn_puede_ver;
- atenciones insert (WITH CHECK), update (USING and WITH CHECK) and delete
  (USING): fn_puede_operar — a role-only predicate, so one check per request
  covers both USING and WITH CHECK;
- fallas_pc write (ALL, USING and WITH CHECK): fn_puede_gestionar_auxiliares;
- solicitudes_baja insert: fn_puede_operar() and estado = 'pendiente' (the input
  schema only accepts 'pendiente' and the row is written with it explicitly);
  resolve (update) and delete: fn_puede_gestionar_auxiliares.
PC states are never updated here: only rpc_cambiar_estado_pcs and
rpc_registrar_reparaciones set `app.cambio_estado_pc` (trigger
fn_trg_pc_estado_controlado). The RPCs validate the role themselves too; the API
checks it first so a missing permission is a 403, not a 422.
"""

import json
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.routers.asignacion.turnos import nombre_de
from app.schemas.asignacion_operacion import (
    AtencionesUpdate,
    AtencionIn,
    CambioEstadoPcs,
    FallaIn,
    FallaUpdate,
    GenerarPcs,
    ReparacionesIn,
    ResolverBaja,
    SolicitudBajaIn,
)
from app.services.asignacion.sql import (
    Permission,
    insert_returning_id,
    not_found,
    require,
    rows,
    update_by_id,
    writing,
)

router = APIRouter()

# Ticket with its ambiente{codigo}, pc{etiqueta}, docente{nombres, apellidos}
# and autor{nombre_completo} embeds (same as the old PostgREST select).
_ATENCION = f"""
    select a.*,
           case when am.id is null then null
                else json_build_object('codigo', am.codigo) end as ambiente,
           case when pc.id is null then null
                else json_build_object('etiqueta', pc.etiqueta) end as pc,
           case when d.id is null then null
                else json_build_object('nombres', d.nombres,
                                       'apellidos', d.apellidos) end as docente,
           {nombre_de("au")} as autor
      from horarios.atenciones a
      left join horarios.ambientes am on am.id = a.ambiente_id
      left join horarios.ambiente_pcs pc on pc.id = a.pc_id
      left join horarios.docentes d on d.id = a.docente_id
      left join horarios.perfiles au on au.id = a.auxiliar_id
"""
# Casts for the atenciones columns that are not plain text/int/bool.
_CASTS = {
    "lote": "uuid",
    "auxiliar_id": "uuid",
    "resuelto_por": "uuid",
    "colaboradores": "uuid[]",
    "fallas": "bigint[]",
    "detalles": "jsonb",
    "resuelto_en": "timestamptz",
}
_SOLICITUD = f"""
    select s.*,
           case when pc.id is null then null
                else json_build_object(
                       'etiqueta', pc.etiqueta,
                       'ambiente', case when am.id is null then null
                                        else json_build_object('codigo', am.codigo)
                                   end) end as pc,
           {nombre_de("au")} as autor
      from horarios.solicitudes_baja s
      left join horarios.ambiente_pcs pc on pc.id = s.pc_id
      left join horarios.ambientes am on am.id = pc.ambiente_id
      left join horarios.perfiles au on au.id = s.solicitado_por
"""


def _bind(cambios: AtencionIn) -> dict[str, Any]:
    """Columns the client sent, as DB-bindable values (UUIDs as text, JSON dumped)."""
    values: dict[str, Any] = {}
    for column, value in cambios.model_dump(exclude_unset=True).items():
        if isinstance(value, UUID):
            value = str(value)
        elif column == "colaboradores" and value is not None:
            value = [str(v) for v in value]
        elif column == "detalles" and value is not None:
            value = json.dumps(value)
        values[column] = value
    return values


def _placeholder(column: str) -> str:
    cast = _CASTS.get(column)
    return f"cast(:{column} as {cast})" if cast else f":{column}"


def _atencion(db: Session, atencion_id: int) -> dict:
    found = rows(db, text(f"{_ATENCION} where a.id = :id"), {"id": atencion_id})
    if not found:
        raise not_found()
    return dict(found[0])


# --- atenciones ------------------------------------------------------------------


@router.get("/atenciones")
def listar_atenciones(
    db: AsignacionDb,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
    ambiente_id: int | None = None,
    participante: UUID | None = None,
) -> list[dict]:
    """Tickets, newest first. `desde`/`hasta` are whole days in America/La_Paz;
    `participante` = author or collaborator."""
    require(db, Permission.VER)
    where, params = [], {}
    if desde:
        where.append(
            "a.creado_en >= cast(:desde as date)::timestamp at time zone 'America/La_Paz'"
        )
        params["desde"] = desde
    if hasta:
        where.append(
            "a.creado_en < (cast(:hasta as date) + 1)::timestamp"
            " at time zone 'America/La_Paz'"
        )
        params["hasta"] = hasta
    if estado:
        where.append("a.estado = :estado")
        params["estado"] = estado
    if ambiente_id:
        where.append("a.ambiente_id = :ambiente_id")
        params["ambiente_id"] = ambiente_id
    if participante:
        where.append(
            "(a.auxiliar_id = cast(:p as uuid) or cast(:p as uuid) = any(a.colaboradores))"
        )
        params["p"] = str(participante)
    sql = _ATENCION + (f" where {' and '.join(where)}" if where else "")
    sql += " order by a.creado_en desc, a.id desc"
    return [dict(r) for r in rows(db, text(sql), params)]


@router.get("/atenciones/arrastradas")
def atenciones_arrastradas(db: AsignacionDb) -> list[dict]:
    """Unresolved tickets carried over between shifts (pase de turno)."""
    require(db, Permission.VER)
    sql = text(
        f"{_ATENCION} where a.estado in ('pendiente', 'en_proceso')"
        " order by a.prioridad, a.creado_en, a.id"
    )
    return [dict(r) for r in rows(db, sql)]


@router.post("/atenciones", status_code=201)
def crear_atenciones(body: list[AtencionIn], db: AsignacionDb) -> list[dict]:
    """Create several tickets at once; returns their id and PC."""
    require(db, Permission.OPERAR)
    creados = []
    with writing(db):
        for fila in body:
            values = _bind(fila)
            if values:
                columns = ", ".join(values)
                params = ", ".join(_placeholder(c) for c in values)
                sql = (
                    f"insert into horarios.atenciones ({columns}) values ({params})"
                    " returning id, pc_id"
                )
            else:
                sql = (
                    "insert into horarios.atenciones default values returning id, pc_id"
                )
            creados.append(dict(db.execute(text(sql), values).mappings().one()))
    return creados


@router.patch("/atenciones")
def actualizar_atenciones(body: AtencionesUpdate, db: AsignacionDb) -> dict:
    """Apply the same changes to several tickets."""
    require(db, Permission.OPERAR)
    values = _bind(body.cambios)
    if not values:
        return {"actualizadas": 0}
    assignments = ", ".join(f"{c} = {_placeholder(c)}" for c in values)
    sql = text(
        f"update horarios.atenciones set {assignments} where id = any(:_ids)"
        " returning id"
    )
    with writing(db):
        n = len(db.execute(sql, {**values, "_ids": body.ids}).all())
    return {"actualizadas": n}


@router.patch("/atenciones/{atencion_id}")
def actualizar_atencion(atencion_id: int, body: AtencionIn, db: AsignacionDb) -> dict:
    require(db, Permission.OPERAR)
    values = _bind(body)
    with writing(db):
        if values:
            assignments = ", ".join(f"{c} = {_placeholder(c)}" for c in values)
            sql = text(
                f"update horarios.atenciones set {assignments} where id = :_id"
                " returning id"
            )
            found = db.execute(sql, {**values, "_id": atencion_id}).first()
            if found is None:
                raise not_found()
    return _atencion(db, atencion_id)


@router.delete("/atenciones", status_code=204)
def eliminar_atenciones(
    db: AsignacionDb, id: Annotated[list[int], Query(min_length=1)]
) -> Response:
    require(db, Permission.OPERAR)
    with writing(db):
        db.execute(
            text("delete from horarios.atenciones where id = any(:ids)"), {"ids": id}
        )
    return Response(status_code=204)


# --- estado de PCs ---------------------------------------------------------------


@router.post("/ambiente-pcs/estado")
def cambiar_estado_pcs(body: CambioEstadoPcs, db: AsignacionDb) -> dict:
    """rpc_cambiar_estado_pcs: the only way to change PC states (leaves a ticket)."""
    require(db, Permission.OPERAR)
    sql = text(
        "select horarios.rpc_cambiar_estado_pcs("
        "cast(:ids as bigint[]), :estado, :detalle, :ticket)"
    )
    with writing(db):
        n = db.execute(
            sql,
            {
                "ids": body.ids,
                "estado": body.estado,
                "detalle": body.detalle,
                "ticket": body.ticket,
            },
        ).scalar_one()
    return {"cambiadas": n}


@router.get("/ambiente-pcs/mis-bajas")
def mis_bajas(db: AsignacionDb, desde: datetime) -> list[dict]:
    """PCs the requester put de baja since `desde` (ISO timestamp), oldest first."""
    require(db, Permission.VER)
    sql = text(
        """
        select p.etiqueta, p.motivo_baja, p.estado_detalle, p.estado_en,
               case when am.id is null then null
                    else json_build_object('codigo', am.codigo) end as ambiente
          from horarios.ambiente_pcs p
          left join horarios.ambientes am on am.id = p.ambiente_id
         where p.estado = 'baja' and p.estado_por = horarios.fn_usuario_actual()
           and p.estado_en >= :desde
         order by p.estado_en
        """
    )
    return [dict(r) for r in rows(db, sql, {"desde": desde})]


@router.post("/ambientes/{ambiente_id}/pcs/generar")
def generar_pcs(ambiente_id: int, body: GenerarPcs, db: AsignacionDb) -> dict:
    """fn_generar_pcs: the teacher PC plus `cantidad` numbered student PCs."""
    require(db, Permission.OPERAR)
    sql = text("select horarios.fn_generar_pcs(:a, :n)")
    with writing(db):
        n = db.execute(sql, {"a": ambiente_id, "n": body.cantidad}).scalar_one()
    return {"creadas": n}


# --- fallas y fichas de reparación -----------------------------------------------


@router.get("/fallas-pc")
def listar_fallas(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    sql = text("select * from horarios.fallas_pc order by orden, nombre")
    return [dict(r) for r in rows(db, sql)]


def _falla(db: Session, falla_id: int) -> dict:
    sql = text("select * from horarios.fallas_pc where id = :id")
    found = rows(db, sql, {"id": falla_id})
    if not found:
        raise not_found()
    return dict(found[0])


@router.post("/fallas-pc", status_code=201)
def crear_falla(body: FallaIn, db: AsignacionDb) -> dict:
    require(db, Permission.GESTIONAR_AUXILIARES)
    values = body.model_dump()
    values["nombre"] = values["nombre"].strip()
    with writing(db):
        falla_id = insert_returning_id(db, "fallas_pc", values)
    return _falla(db, falla_id)


@router.patch("/fallas-pc/{falla_id}")
def actualizar_falla(falla_id: int, body: FallaUpdate, db: AsignacionDb) -> dict:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not update_by_id(
            db, "fallas_pc", falla_id, body.model_dump(exclude_unset=True)
        ):
            raise not_found()
    return _falla(db, falla_id)


@router.post("/reparaciones")
def registrar_reparaciones(body: ReparacionesIn, db: AsignacionDb) -> dict:
    """rpc_registrar_reparaciones: one correctivo ticket per PC plus its state."""
    require(db, Permission.OPERAR)
    sql = text(
        "select horarios.rpc_registrar_reparaciones("
        "cast(:fichas as jsonb), cast(:colaboradores as uuid[]), :prioridad)"
    )
    params = {
        "fichas": json.dumps([f.model_dump(mode="json") for f in body.fichas]),
        "colaboradores": [str(c) for c in body.colaboradores],
        "prioridad": body.prioridad,
    }
    with writing(db):
        n = db.execute(sql, params).scalar_one()
    return {"registradas": n}


# --- solicitudes de baja ---------------------------------------------------------


@router.get("/solicitudes-baja")
def listar_solicitudes_baja(db: AsignacionDb, estado: str = "pendiente") -> list[dict]:
    """Baja requests (pending by default), oldest first."""
    require(db, Permission.VER)
    sql = text(f"{_SOLICITUD} where s.estado = :estado order by s.solicitado_en, s.id")
    return [dict(r) for r in rows(db, sql, {"estado": estado})]


@router.post("/solicitudes-baja", status_code=201)
def crear_solicitudes_baja(body: list[SolicitudBajaIn], db: AsignacionDb) -> list[dict]:
    """Request the baja of PCs; always written as 'pendiente' (old WITH CHECK)."""
    require(db, Permission.OPERAR)
    sql = text(
        """
        insert into horarios.solicitudes_baja (pc_id, motivo, atencion_id, estado)
        values (:pc_id, :motivo, :atencion_id, 'pendiente')
        returning id
        """
    )
    with writing(db):
        ids = [
            db.execute(
                sql,
                {"pc_id": s.pc_id, "motivo": s.motivo, "atencion_id": s.atencion_id},
            ).scalar_one()
            for s in body
        ]
    return [{"id": i} for i in ids]


@router.post("/solicitudes-baja/{solicitud_id}/resolver")
def resolver_baja(solicitud_id: int, body: ResolverBaja, db: AsignacionDb) -> dict:
    """rpc_resolver_baja (admin/encargado): approve (PC de baja) or reject."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    sql = text("select horarios.rpc_resolver_baja(:id, :aprobar, :respuesta)")
    with writing(db):
        db.execute(
            sql,
            {"id": solicitud_id, "aprobar": body.aprobar, "respuesta": body.respuesta},
        )
    return {"id": solicitud_id, "estado": "aprobada" if body.aprobar else "rechazada"}
