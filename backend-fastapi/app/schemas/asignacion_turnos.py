"""Input schemas for auxiliar shifts and shift reports (schema `horarios`).

Outputs are the rows the Angular app used to read from PostgREST (`select('*')`
plus the same embeds), returned as plain dicts. Inputs forbid unknown fields.
"""

from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

TurnoCodigo = Literal["M", "MD", "T", "N"]


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


class RotacionCreate(_In):
    fecha: date
    auxiliar_id: UUID | None = None
    turno: TurnoCodigo | None = None
    nota: str | None = None


class RotacionUpdate(_In):
    fecha: date | None = None
    auxiliar_id: UUID | None = None
    turno: TurnoCodigo | None = None
    nota: str | None = None


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


class TareaMarca(_In):
    hecha: bool
