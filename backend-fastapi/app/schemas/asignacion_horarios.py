"""Schemas for academic scheduling (asignaciones, cesiones, reservas, occupancy).

Write payloads are passed whole, as one `jsonb` argument, to the ported SQL RPCs
(rpc_guardar_asignacion, rpc_guardar_cesiones, rpc_guardar_reserva,
rpc_reubicar_clase), which own their validation; so they are plain JSON objects
here. Query bodies are typed and forbid unknown fields.

Outputs are the rows/embeds the Angular app used to get from PostgREST and are
returned as-is (dates `YYYY-MM-DD`, times `HH:MM:SS`).
"""

from datetime import date, time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# JSON object handed unchanged to an rpc_* function as its `p jsonb` argument.
RpcPayload = dict[str, Any]

TipoAmbiente = Literal["laboratorio", "aula", "auditorio", "otro"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IgnorarChoque(_In):
    """What a clash check must ignore (the record being edited)."""

    asignacion_id: int | None = None
    reserva_id: int | None = None
    cesion_id: int | None = None
    asignacion_horario_ids: list[int] | None = None
    asignacion_horario_id: int | None = None


class CandidatoChoque(_In):
    fecha: date | None = None
    dia_semana: int | None = None
    desde: date | None = None
    hasta: date | None = None
    hora_inicio: time
    hora_fin: time
    ambiente_id: int | None = None
    docente_id: int | None = None


class VerificarChoquesIn(_In):
    items: list[CandidatoChoque]
    ignorar: IgnorarChoque = Field(default_factory=IgnorarChoque)


class AmbientesLibresIn(_In):
    fecha: date
    hora_inicio: time
    hora_fin: time
    tipo: TipoAmbiente | None = None
    ignorar: IgnorarChoque = Field(default_factory=IgnorarChoque)


class AmbientesLibresFechasIn(_In):
    fechas: list[date]
    hora_inicio: time
    hora_fin: time
    tipo: TipoAmbiente | None = None
    ignorar: IgnorarChoque = Field(default_factory=IgnorarChoque)


class IdOut(BaseModel):
    id: int


class LoteOut(BaseModel):
    lote: UUID
