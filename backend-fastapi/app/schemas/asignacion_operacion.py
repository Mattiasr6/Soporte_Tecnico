"""Input schemas for auxiliar operation (schema `horarios`): tickets, repair
forms, PC state changes and baja requests.

Outputs are the rows the Angular app used to read from PostgREST (`select('*')`
plus the same embeds), returned as plain dicts. Inputs forbid unknown fields;
value rules (lengths, enums, ranges) stay in the DB constraints and RPCs.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EstadoPc = Literal["operativa", "inactiva", "mantenimiento", "baja"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AtencionIn(_In):
    """Writable columns of atenciones (only the ones sent are written)."""

    turno_trabajo_id: int | None = None
    ambiente_id: int | None = None
    pc_id: int | None = None
    docente_id: int | None = None
    solicitante: str | None = None
    tipo: str | None = None
    alcance: str | None = None
    descripcion: str | None = None
    solucion: str | None = None
    lote: UUID | None = None
    colaboradores: list[UUID] | None = None
    detalles: dict[str, Any] | None = None
    prioridad: int | None = None
    estado: str | None = None
    auxiliar_id: UUID | None = None
    resuelto_por: UUID | None = None
    resuelto_en: datetime | None = None
    fallas: list[int] | None = None
    falla_otra: str | None = None
    pieza: str | None = None
    estado_anterior: str | None = None
    estado_final: str | None = None
    # Django LabAtenciones fields: turno M/MD/T/N (the DB defaults it from the
    # work shift or the ticket time) and medio_solicitud Presencial/WhatsApp.
    turno: str | None = None
    medio_solicitud: str | None = None


class AtencionesUpdate(_In):
    """Same changes applied to several tickets (e.g. a whole lote)."""

    ids: list[int] = Field(min_length=1, max_length=500)
    cambios: AtencionIn


class CambioEstadoPcs(_In):
    ids: list[int] = Field(min_length=1, max_length=500)
    estado: EstadoPc
    detalle: str = ""
    ticket: bool = True


class GenerarPcs(_In):
    cantidad: int


class FallaIn(_In):
    nombre: str
    categoria: str = "otro"
    orden: int = 100
    activo: bool = True


class FallaUpdate(_In):
    nombre: str | None = None
    categoria: str | None = None
    activo: bool | None = None
    orden: int | None = None


class FichaReparacion(_In):
    pc_id: int
    fallas: list[int] = []
    falla_otra: str | None = None
    diagnostico: str | None = None
    correccion: str | None = None
    pieza: str | None = None
    estado_final: EstadoPc | None = None


class ReparacionesIn(_In):
    fichas: list[FichaReparacion]
    colaboradores: list[UUID] = []
    prioridad: int = 2


class SolicitudBajaIn(_In):
    """Old RLS: insert only with estado = 'pendiente' (anything else -> 422)."""

    pc_id: int
    motivo: str
    atencion_id: int | None = None
    estado: Literal["pendiente"] = "pendiente"


class ResolverBaja(_In):
    aprobar: bool
    respuesta: str | None = None
