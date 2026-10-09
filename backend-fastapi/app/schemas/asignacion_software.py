"""Input schemas for the software inventory and attention templates (G7).

Ported from the Soporte `app/schemas/software.py`. Lengths and the unique name
stay in the DB constraints (migration 0027); enums are also checked here so a
wrong value is a 422 before any query.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.asignacion_turnos import TurnoCodigo

Licencia = Literal["gratuita", "mixta", "paga"]
EstadoSoftwarePc = Literal["instalado", "falta", "dañado"]
# Attention tipos a template can prefill (correctivo and cambio_estado go
# through their own RPC flows in the attention form).
TipoPlantilla = Literal["docente", "programas", "preventivo", "personal"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SoftwareIn(_In):
    """Whole software row (Django sent every field on create and edit)."""

    nombre: str
    licencia: Licencia = "gratuita"
    uso: str = ""
    esencial: bool = False
    docentes: bool = False
    activo: bool = True


class AmbienteSoftwareIn(_In):
    """Full software list of a lab: replaces the previous one."""

    software_ids: list[int] = Field(default_factory=list, max_length=500)


class PcSoftwareIn(_In):
    estado: EstadoSoftwarePc


class PlantillaAtencionIn(_In):
    nombre: str
    tipo: TipoPlantilla = "programas"
    descripcion: str = ""
    solucion: str = ""
    turno: TurnoCodigo | None = None
    activa: bool = True
