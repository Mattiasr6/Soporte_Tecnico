"""Performance dashboards (old Supabase RPCs fn_dashboard_operacion|uso|detalle|fallas,
plus fn_dashboard_laboratorios ported from the Django lab dashboard).

All the SQL functions only allow fn_puede_gestionar_auxiliares (admin or
encargado; the Angular route uses the same guard), so the API checks it first
and a missing permission is a 403 instead of a 422 from the function.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_dashboards import FiltroLaboratorios, RangoDashboard
from app.services.asignacion.dashboards import (
    Dashboard,
    obtener,
    obtener_laboratorios,
)

router = APIRouter(prefix="/dashboard")


# Declared before /{dashboard} so it is not taken as an unknown dashboard name.
@router.get("/laboratorios")
def dashboard_laboratorios(
    filtro: Annotated[FiltroLaboratorios, Query()], db: AsignacionDb
) -> dict[str, Any]:
    """fn_dashboard_laboratorios (Django lab dashboard + reports): per lab x
    tipo/turno, counts by tipo/turno/medio and the year trend."""
    return obtener_laboratorios(db, filtro)


@router.get("/{dashboard}")
def dashboard(
    dashboard: Dashboard,
    rango: Annotated[RangoDashboard, Query()],
    db: AsignacionDb,
) -> dict[str, Any]:
    return obtener(db, dashboard, rango)
