"""Saturday planner (Django `auxiliares/horarios-sabados/`).

Permissions follow the rotacion_sabados RLS rules (99_rls_reference.sql):
read with fn_puede_ver, plan and clear with fn_puede_gestionar_auxiliares
(admin/encargado; Django: Jefe, dashboard viewers and Encargado). The rules
live in `app.services.asignacion.sabados`.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_turnos import SabadoIn
from app.services.asignacion import sabados as servicio
from app.services.asignacion.sql import Permission, not_found, require, writing

router = APIRouter()


@router.get("/sabados")
def listar_sabados(
    db: AsignacionDb,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    anio: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> dict[str, Any]:
    """Every Saturday of a month (default: this La Paz month) with its plan."""
    require(db, Permission.VER)
    hoy = servicio.hoy()
    return servicio.mes(db, anio or hoy.year, mes or hoy.month)


@router.put("/sabados/{fecha}")
def planificar_sabado(fecha: date, body: SabadoIn, db: AsignacionDb) -> dict[str, Any]:
    """Replace the plan of one Saturday (several auxiliares per turno, own hours)."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    return servicio.guardar(db, fecha, body)


@router.delete("/sabados/{fecha}", status_code=204)
def limpiar_sabado(fecha: date, db: AsignacionDb) -> Response:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not servicio.limpiar_fecha(db, fecha):
            raise not_found()
    return Response(status_code=204)
