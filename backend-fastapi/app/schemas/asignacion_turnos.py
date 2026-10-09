"""Input schemas for auxiliar shifts and shift reports (schema `horarios`).

Outputs are the rows the Angular app used to read from PostgREST (`select('*')`
plus the same embeds), returned as plain dicts. Inputs forbid unknown fields.
"""

from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TurnoCodigo = Literal["M", "MD", "T", "N"]
# Saturdays have no night shift (Django: mañana, mediodia, tarde).
TurnoSabado = Literal["M", "MD", "T"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TurnoProgramadoFila(_In):
    perfil_id: UUID
    turno: TurnoCodigo


class TurnosProgramadosIn(_In):
    """Shifts of several auxiliares from one date (existing date = changed)."""

    desde: date
    filas: list[TurnoProgramadoFila]


class HorarioTurnoIn(_In):
    turno: TurnoCodigo
    hora_inicio: time
    hora_fin: time


class AsignarTurnoIn(_In):
    turno: TurnoCodigo | None = None
    sabado: bool = False


class SabadoTurnoIn(_In):
    """One turno of a planned Saturday: its auxiliares and optional own hours."""

    turno: TurnoSabado
    hora_inicio: time | None = None
    hora_fin: time | None = None
    auxiliares: list[UUID] = []

    @model_validator(mode="after")
    def _horas(self) -> "SabadoTurnoIn":
        if (self.hora_inicio is None) != (self.hora_fin is None):
            raise ValueError("Pon la hora de inicio y la de fin, o ninguna.")
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora de fin debe ser después de la de inicio.")
        return self


class SabadoIn(_In):
    """Whole plan of one Saturday (replaces what the date had)."""

    nota: str | None = Field(default=None, max_length=200)
    turnos: list[SabadoTurnoIn] = []

    @model_validator(mode="after")
    def _unicos(self) -> "SabadoIn":
        codigos = [t.turno for t in self.turnos]
        if len(codigos) != len(set(codigos)):
            raise ValueError("Cada turno va una sola vez.")
        ids = [a for t in self.turnos for a in t.auxiliares]
        if len(ids) != len(set(ids)):
            raise ValueError("Un auxiliar solo puede estar en un turno del sábado.")
        return self


class AbrirTurnoIn(_In):
    turno: TurnoCodigo
    es_sabado_rotativo: bool = False
    notas: str | None = None


class CerrarTurnoIn(_In):
    notas: str | None = None


class TareaNueva(_In):
    descripcion: str
    ambiente_id: int | None = None


class TareaEdicion(TareaNueva):
    id: int | None = None


class ReporteCreate(_In):
    turno: TurnoCodigo
    novedades: str | None = None
    # Defaults to the requesting user; someone else's needs gestionar.
    auxiliar_id: UUID | None = None
    tareas: list[TareaNueva] = []


class ReporteUpdate(_In):
    turno: TurnoCodigo
    novedades: str | None = None


class ReporteDecision(_In):
    """Validate or reject a pending shift close (Jefe/Encargado, not the author)."""

    estado: Literal["validado", "rechazado"]


class TareaMarca(_In):
    hecha: bool
