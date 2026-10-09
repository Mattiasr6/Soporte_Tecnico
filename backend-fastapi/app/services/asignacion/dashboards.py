"""Dashboards of the asignacion module: the SQL functions horarios.fn_dashboard_*.

Each function takes `(p_desde date, p_hasta date)`, checks
fn_puede_gestionar_auxiliares and the range itself, and returns one jsonb
object. The API checks both first (403/422); a SQL rejection that still happens
(e.g. fn_dashboard_operacion counts the range inclusively) maps to the same
HTTP errors as any other DB error of the module.
"""

from enum import StrEnum
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.schemas.asignacion_dashboards import RangoDashboard
from app.services.asignacion.sql import Permission, http_error_from_db, require


class Dashboard(StrEnum):
    """Whitelisted dashboards (value = suffix of horarios.fn_dashboard_<value>)."""

    OPERACION = "operacion"
    USO = "uso"
    DETALLE = "detalle"
    FALLAS = "fallas"


_SQL = {
    d: text(f"select horarios.fn_dashboard_{d.value}(:desde, :hasta)")
    for d in Dashboard
}


def obtener(db: Session, dashboard: Dashboard, rango: RangoDashboard) -> Any:
    """Run the dashboard function for the requesting user and return its JSON."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    try:
        return db.execute(
            _SQL[dashboard], {"desde": rango.desde, "hasta": rango.hasta}
        ).scalar_one()
    except DBAPIError as exc:
        db.rollback()
        mapped = http_error_from_db(exc)
        if mapped is None:
            raise
        raise mapped from None
