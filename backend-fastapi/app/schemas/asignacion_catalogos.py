"""Schemas for the asignacion catalogs (Postgres schema `horarios`).

Outputs mirror the JSON the Angular app used to get from PostgREST
(`select('*')` plus the same embeds), so the templates keep working unchanged.
Inputs forbid unknown fields: their field names are the only column names the
write helpers ever put into SQL.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- carreras -----------------------------------------------------------------


class CarreraOut(BaseModel):
    id: int
    nombre: str
    sigla: str | None
    color: str
    activo: bool
    creado_en: datetime
    actualizado_en: datetime


class CarreraCreate(_In):
    nombre: str
    sigla: str | None = None
    color: str | None = None
    activo: bool | None = None


class CarreraUpdate(_In):
    nombre: str | None = None
    sigla: str | None = None
    color: str | None = None
    activo: bool | None = None


# --- materias -----------------------------------------------------------------


class MateriaOut(BaseModel):
    id: int
    nombre: str
    sigla: str | None
    requiere_laboratorio: bool
    activo: bool
    creado_en: datetime
    actualizado_en: datetime


class MateriaCreate(_In):
    nombre: str
    sigla: str | None = None
    requiere_laboratorio: bool | None = None
    activo: bool | None = None


class MateriaUpdate(_In):
    nombre: str | None = None
    sigla: str | None = None
    requiere_laboratorio: bool | None = None
    activo: bool | None = None


# --- docentes -----------------------------------------------------------------


class DocenteCarreraRef(BaseModel):
    carrera_id: int


class DocenteMateriaRef(BaseModel):
    materia_id: int


class DocenteOut(BaseModel):
    id: int
    nombres: str
    apellidos: str
    carnet: str | None
    telefono: str | None
    correo: str | None
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    docente_carreras: list[DocenteCarreraRef]
    docente_materias: list[DocenteMateriaRef]


class DocenteCreate(_In):
    nombres: str
    apellidos: str
    carnet: str | None = None
    telefono: str | None = None
    correo: str | None = None
    activo: bool | None = None


class DocenteUpdate(_In):
    nombres: str | None = None
    apellidos: str | None = None
    carnet: str | None = None
    telefono: str | None = None
    correo: str | None = None
    activo: bool | None = None


class DocenteRelaciones(_In):
    """Full replacement of the docente's carreras and materias."""

    carreras: list[int]
    materias: list[int]


# --- ambientes ----------------------------------------------------------------


class AmbienteOut(BaseModel):
    id: int
    codigo: str
    nombre: str | None
    tipo: str
    capacidad: int
    tipo_equipo: str | None
    ubicacion: str | None
    estado: str
    color: str
    orden: int
    # lab hardware sheet (G8): declared standard spec, nullable
    procesador: str | None = None
    ram: str | None = None
    almacenamiento: str | None = None
    marca: str | None = None
    gpu: str | None = None
    monitores: str | None = None
    sillas: int | None = None
    pcs_estudiantes: int | None = None
    pcs_docentes: int | None = None
    creado_en: datetime
    actualizado_en: datetime


class AmbienteCreate(_In):
    codigo: str
    nombre: str | None = None
    tipo: str | None = None
    capacidad: int | None = None
    tipo_equipo: str | None = None
    ubicacion: str | None = None
    estado: str | None = None
    color: str | None = None
    orden: int | None = None


class AmbienteUpdate(_In):
    codigo: str | None = None
    nombre: str | None = None
    tipo: str | None = None
    capacidad: int | None = None
    tipo_equipo: str | None = None
    ubicacion: str | None = None
    estado: str | None = None
    color: str | None = None
    orden: int | None = None


class AmbienteFichaIn(_In):
    """Whole lab sheet (PUT replaces it): a missing or blank field is cleared.

    `capacidad` is shared with the academic assignment (NOT NULL), so a missing
    or null value keeps the current one instead of clearing it. Sizes and
    ranges are checked by the DB (422 with code 23514).
    """

    procesador: str | None = None
    ram: str | None = None
    almacenamiento: str | None = None
    marca: str | None = None
    gpu: str | None = None
    monitores: str | None = None
    sillas: int | None = None
    capacidad: int | None = None
    pcs_estudiantes: int | None = None
    pcs_docentes: int | None = None


# --- ambiente_pcs -------------------------------------------------------------


class PerfilNombre(BaseModel):
    nombre_completo: str


class AmbientePcOut(BaseModel):
    id: int
    ambiente_id: int
    etiqueta: str
    procesador: str | None
    ram: str | None
    almacenamiento: str | None
    estado: str
    notas: str | None
    orden: int
    es_docente: bool
    motivo_baja: str | None
    baja_en: datetime | None
    baja_por: UUID | None
    estado_por: UUID | None
    estado_en: datetime | None
    estado_detalle: str | None
    creado_en: datetime
    actualizado_en: datetime
    # PostgREST embed `cambio:perfiles!ambiente_pcs_estado_por_fkey(nombre_completo)`
    cambio: PerfilNombre | None


class AmbientePcCreate(_In):
    ambiente_id: int
    etiqueta: str
    procesador: str | None = None
    ram: str | None = None
    almacenamiento: str | None = None
    notas: str | None = None
    orden: int | None = None
    es_docente: bool | None = None
    estado: str | None = None
    motivo_baja: str | None = None


class AmbientePcUpdate(_In):
    # `estado` stays accepted: trigger fn_trg_pc_estado_controlado rejects a direct
    # change with its own message (state changes go through rpc_cambiar_estado_pcs).
    ambiente_id: int | None = None
    etiqueta: str | None = None
    procesador: str | None = None
    ram: str | None = None
    almacenamiento: str | None = None
    notas: str | None = None
    orden: int | None = None
    es_docente: bool | None = None
    estado: str | None = None
    motivo_baja: str | None = None


# --- read-only catalogs -------------------------------------------------------


class SistemaAcademicoOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    dias_permitidos: list[int]
    modo_fechas: str
    meses_duracion: int | None
    meses_maximo: int | None
    dias_sugeridos: int | None
    color: str
    activo: bool


class BloqueHorarioOut(BaseModel):
    id: int
    nombre: str
    turno: str
    hora_inicio: time
    hora_fin: time
    orden: int


class TipoReservaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    prioridad: int
    color: str


# --- feriados -----------------------------------------------------------------


class FeriadoOut(BaseModel):
    fecha: date
    descripcion: str


class FeriadoIn(_In):
    descripcion: str
