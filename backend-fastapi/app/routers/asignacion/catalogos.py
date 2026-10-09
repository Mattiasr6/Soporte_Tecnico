"""Catalog endpoints of the asignacion module (ex Supabase tables in `horarios`).

Permissions follow the old RLS policies (99_rls_reference.sql):
- read: fn_puede_ver (every active role except invitado);
- carreras, materias, docentes (+ relations), ambientes, feriados: fn_puede_editar;
- ambiente_pcs: create/update fn_puede_operar, delete fn_puede_gestionar_auxiliares;
- sistemas_academicos, bloques_horario, tipos_reserva: read-only here (the UI
  never edits them; their RLS write rule was fn_es_admin).
Orderings and embeds match the PostgREST queries the Angular app used.
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_catalogos import (
    AmbienteCreate,
    AmbienteOut,
    AmbientePcCreate,
    AmbientePcOut,
    AmbientePcUpdate,
    AmbienteUpdate,
    BloqueHorarioOut,
    CarreraCreate,
    CarreraOut,
    CarreraUpdate,
    DocenteCreate,
    DocenteOut,
    DocenteRelaciones,
    DocenteUpdate,
    FeriadoIn,
    FeriadoOut,
    MateriaCreate,
    MateriaOut,
    MateriaUpdate,
    SistemaAcademicoOut,
    TipoReservaOut,
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

TipoAmbiente = Literal["laboratorio", "aula", "auditorio", "otro"]

# --- SQL ----------------------------------------------------------------------

_CARRERAS = "select * from horarios.carreras"
_MATERIAS = "select * from horarios.materias"
_AMBIENTES = "select * from horarios.ambientes"
_DOCENTES = """
    select d.*,
           coalesce((select json_agg(json_build_object('carrera_id', dc.carrera_id)
                                     order by dc.carrera_id)
                       from horarios.docente_carreras dc
                      where dc.docente_id = d.id), '[]'::json) as docente_carreras,
           coalesce((select json_agg(json_build_object('materia_id', dm.materia_id)
                                     order by dm.materia_id)
                       from horarios.docente_materias dm
                      where dm.docente_id = d.id), '[]'::json) as docente_materias
      from horarios.docentes d
"""
_PCS = """
    select p.*,
           case when pf.id is null then null
                else json_build_object('nombre_completo', pf.nombre_completo)
           end as cambio
      from horarios.ambiente_pcs p
      left join horarios.perfiles pf on pf.id = p.estado_por
"""


def _one(db: Session, base: str, alias: str, row_id: int) -> dict:
    found = rows(db, text(f"{base} where {alias}id = :id"), {"id": row_id})
    if not found:
        raise not_found()
    return dict(found[0])


def _create(db: Session, table: str, values: dict, permission: Permission) -> int:
    require(db, permission)
    with writing(db):
        new_id = insert_returning_id(db, table, values)
    return new_id


def _update(
    db: Session, table: str, row_id: int, values: dict, permission: Permission
) -> None:
    require(db, permission)
    with writing(db):
        exists = update_by_id(db, table, row_id, values)
    if not exists:
        raise not_found()


def _delete(db: Session, table: str, row_id: int, permission: Permission) -> Response:
    require(db, permission)
    with writing(db):
        deleted = delete_by_id(db, table, row_id)
    if not deleted:
        raise not_found()
    return Response(status_code=204)


# --- carreras -----------------------------------------------------------------


@router.get("/carreras", response_model=list[CarreraOut])
def list_carreras(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [dict(r) for r in rows(db, text(f"{_CARRERAS} order by nombre"))]


@router.post("/carreras", response_model=CarreraOut, status_code=201)
def create_carrera(body: CarreraCreate, db: AsignacionDb) -> dict:
    new_id = _create(
        db, "carreras", body.model_dump(exclude_unset=True), Permission.EDITAR
    )
    return _one(db, _CARRERAS, "", new_id)


@router.patch("/carreras/{carrera_id}", response_model=CarreraOut)
def update_carrera(carrera_id: int, body: CarreraUpdate, db: AsignacionDb) -> dict:
    _update(
        db,
        "carreras",
        carrera_id,
        body.model_dump(exclude_unset=True),
        Permission.EDITAR,
    )
    return _one(db, _CARRERAS, "", carrera_id)


@router.delete("/carreras/{carrera_id}", status_code=204)
def delete_carrera(carrera_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "carreras", carrera_id, Permission.EDITAR)


# --- materias -----------------------------------------------------------------


@router.get("/materias", response_model=list[MateriaOut])
def list_materias(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [dict(r) for r in rows(db, text(f"{_MATERIAS} order by nombre"))]


@router.post("/materias", response_model=MateriaOut, status_code=201)
def create_materia(body: MateriaCreate, db: AsignacionDb) -> dict:
    new_id = _create(
        db, "materias", body.model_dump(exclude_unset=True), Permission.EDITAR
    )
    return _one(db, _MATERIAS, "", new_id)


@router.patch("/materias/{materia_id}", response_model=MateriaOut)
def update_materia(materia_id: int, body: MateriaUpdate, db: AsignacionDb) -> dict:
    _update(
        db,
        "materias",
        materia_id,
        body.model_dump(exclude_unset=True),
        Permission.EDITAR,
    )
    return _one(db, _MATERIAS, "", materia_id)


@router.delete("/materias/{materia_id}", status_code=204)
def delete_materia(materia_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "materias", materia_id, Permission.EDITAR)


# --- docentes -----------------------------------------------------------------


@router.get("/docentes", response_model=list[DocenteOut])
def list_docentes(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [
        dict(r) for r in rows(db, text(f"{_DOCENTES} order by d.apellidos, d.nombres"))
    ]


@router.post("/docentes", response_model=DocenteOut, status_code=201)
def create_docente(body: DocenteCreate, db: AsignacionDb) -> dict:
    new_id = _create(
        db, "docentes", body.model_dump(exclude_unset=True), Permission.EDITAR
    )
    return _one(db, _DOCENTES, "d.", new_id)


@router.patch("/docentes/{docente_id}", response_model=DocenteOut)
def update_docente(docente_id: int, body: DocenteUpdate, db: AsignacionDb) -> dict:
    _update(
        db,
        "docentes",
        docente_id,
        body.model_dump(exclude_unset=True),
        Permission.EDITAR,
    )
    return _one(db, _DOCENTES, "d.", docente_id)


@router.delete("/docentes/{docente_id}", status_code=204)
def delete_docente(docente_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "docentes", docente_id, Permission.EDITAR)


@router.put("/docentes/{docente_id}/relaciones", response_model=DocenteOut)
def replace_docente_relaciones(
    docente_id: int, body: DocenteRelaciones, db: AsignacionDb
) -> dict:
    """Replace the docente's carreras and materias in one transaction."""
    require(db, Permission.EDITAR)
    _one(db, _DOCENTES, "d.", docente_id)
    params = {"id": docente_id}
    with writing(db):
        db.execute(
            text("delete from horarios.docente_carreras where docente_id = :id"), params
        )
        db.execute(
            text("delete from horarios.docente_materias where docente_id = :id"), params
        )
        db.execute(
            text(
                "insert into horarios.docente_carreras (docente_id, carrera_id) "
                "select :id, unnest(cast(:ids as bigint[])) on conflict do nothing"
            ),
            {**params, "ids": sorted(set(body.carreras))},
        )
        db.execute(
            text(
                "insert into horarios.docente_materias (docente_id, materia_id) "
                "select :id, unnest(cast(:ids as bigint[])) on conflict do nothing"
            ),
            {**params, "ids": sorted(set(body.materias))},
        )
    return _one(db, _DOCENTES, "d.", docente_id)


# --- ambientes ----------------------------------------------------------------


@router.get("/ambientes", response_model=list[AmbienteOut])
def list_ambientes(db: AsignacionDb, tipo: TipoAmbiente | None = None) -> list[dict]:
    require(db, Permission.VER)
    sql = f"{_AMBIENTES} where (cast(:tipo as text) is null or tipo = :tipo) order by orden, codigo"
    return [dict(r) for r in rows(db, text(sql), {"tipo": tipo})]


@router.post("/ambientes", response_model=AmbienteOut, status_code=201)
def create_ambiente(body: AmbienteCreate, db: AsignacionDb) -> dict:
    new_id = _create(
        db, "ambientes", body.model_dump(exclude_unset=True), Permission.EDITAR
    )
    return _one(db, _AMBIENTES, "", new_id)


@router.patch("/ambientes/{ambiente_id}", response_model=AmbienteOut)
def update_ambiente(ambiente_id: int, body: AmbienteUpdate, db: AsignacionDb) -> dict:
    _update(
        db,
        "ambientes",
        ambiente_id,
        body.model_dump(exclude_unset=True),
        Permission.EDITAR,
    )
    return _one(db, _AMBIENTES, "", ambiente_id)


@router.delete("/ambientes/{ambiente_id}", status_code=204)
def delete_ambiente(ambiente_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "ambientes", ambiente_id, Permission.EDITAR)


# --- ambiente_pcs -------------------------------------------------------------


@router.get("/ambiente-pcs", response_model=list[AmbientePcOut])
def list_ambiente_pcs(db: AsignacionDb, ambiente_id: int | None = None) -> list[dict]:
    require(db, Permission.VER)
    sql = (
        f"{_PCS} where (cast(:ambiente_id as bigint) is null or p.ambiente_id = :ambiente_id)"
        " order by p.ambiente_id, p.orden, p.etiqueta"
    )
    return [dict(r) for r in rows(db, text(sql), {"ambiente_id": ambiente_id})]


@router.post("/ambiente-pcs", response_model=AmbientePcOut, status_code=201)
def create_ambiente_pc(body: AmbientePcCreate, db: AsignacionDb) -> dict:
    new_id = _create(
        db, "ambiente_pcs", body.model_dump(exclude_unset=True), Permission.OPERAR
    )
    return _one(db, _PCS, "p.", new_id)


@router.patch("/ambiente-pcs/{pc_id}", response_model=AmbientePcOut)
def update_ambiente_pc(pc_id: int, body: AmbientePcUpdate, db: AsignacionDb) -> dict:
    _update(
        db,
        "ambiente_pcs",
        pc_id,
        body.model_dump(exclude_unset=True),
        Permission.OPERAR,
    )
    return _one(db, _PCS, "p.", pc_id)


@router.delete("/ambiente-pcs/{pc_id}", status_code=204)
def delete_ambiente_pc(pc_id: int, db: AsignacionDb) -> Response:
    return _delete(db, "ambiente_pcs", pc_id, Permission.GESTIONAR_AUXILIARES)


# --- read-only catalogs -------------------------------------------------------


@router.get("/sistemas-academicos", response_model=list[SistemaAcademicoOut])
def list_sistemas_academicos(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    sql = text("select * from horarios.sistemas_academicos where activo order by id")
    return [dict(r) for r in rows(db, sql)]


@router.get("/bloques-horario", response_model=list[BloqueHorarioOut])
def list_bloques_horario(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [
        dict(r)
        for r in rows(db, text("select * from horarios.bloques_horario order by orden"))
    ]


@router.get("/tipos-reserva", response_model=list[TipoReservaOut])
def list_tipos_reserva(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [
        dict(r)
        for r in rows(db, text("select * from horarios.tipos_reserva order by id"))
    ]


# --- feriados (key = fecha) ---------------------------------------------------


@router.get("/feriados", response_model=list[FeriadoOut])
def list_feriados(db: AsignacionDb) -> list[dict]:
    require(db, Permission.VER)
    return [
        dict(r)
        for r in rows(db, text("select * from horarios.feriados order by fecha"))
    ]


@router.put("/feriados/{fecha}", response_model=FeriadoOut)
def upsert_feriado(fecha: date, body: FeriadoIn, db: AsignacionDb) -> dict:
    """Create or replace the feriado of that date (the UI used a PostgREST upsert)."""
    require(db, Permission.EDITAR)
    with writing(db):
        db.execute(
            text(
                "insert into horarios.feriados (fecha, descripcion) values (:fecha, :d) "
                "on conflict (fecha) do update set descripcion = excluded.descripcion"
            ),
            {"fecha": fecha, "d": body.descripcion},
        )
    return {"fecha": fecha, "descripcion": body.descripcion}


@router.delete("/feriados/{fecha}", status_code=204)
def delete_feriado(fecha: date, db: AsignacionDb) -> Response:
    require(db, Permission.EDITAR)
    with writing(db):
        deleted = db.execute(
            text("delete from horarios.feriados where fecha = :fecha returning 1"),
            {"fecha": fecha},
        ).first()
    if deleted is None:
        raise not_found()
    return Response(status_code=204)
