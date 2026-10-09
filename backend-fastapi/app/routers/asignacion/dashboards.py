"""Performance dashboards (old Supabase RPCs fn_dashboard_operacion|uso|detalle|fallas).

All four SQL functions only allow fn_puede_gestionar_auxiliares (admin or
encargado; the Angular route uses the same guard), so the API checks it first
and a missing permission is a 403 instead of a 422 from the function.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_dashboards import RangoDashboard
from app.services.asignacion.dashboards import Dashboard, obtener

router = APIRouter(prefix="/dashboard")


@router.get("/{dashboard}")
def dashboard(
    dashboard: Dashboard,
    rango: Annotated[RangoDashboard, Query()],
    db: AsignacionDb,
) -> dict[str, Any]:
    return obtener(db, dashboard, rango)
