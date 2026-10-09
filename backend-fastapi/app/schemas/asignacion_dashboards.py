"""Input schema of the asignacion dashboards (old Supabase RPCs fn_dashboard_*).

The output is the JSON object each SQL function builds, returned unchanged.
"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

# Same bound as the SQL functions: `p_hasta - p_desde > 400` is rejected.
MAX_DIAS = 400


class RangoDashboard(BaseModel):
    """Inclusive date range (La Paz days) sent as `?desde=&hasta=`."""

    model_config = ConfigDict(extra="forbid")

    desde: date
    hasta: date

    @model_validator(mode="after")
    def _rango_valido(self) -> Self:
        if self.hasta < self.desde or (self.hasta - self.desde).days > MAX_DIAS:
            raise ValueError("Rango de fechas inválido.")
        return self


class FiltroLaboratorios(RangoDashboard):
    """Lab dashboard/report filters (Django lab_reportes): optional turno and lab."""

    turno: Literal["M", "MD", "T", "N"] | None = None
    ambiente_id: int | None = None
