"""Lab traffic-light board and day timeline (Django `auxiliares/tablero/` and
`auxiliares/timeline/`), read-only.

Permission: fn_puede_ver. Django showed the board to Jefe/dashboard viewers and
the Encargado, and the timeline to everyone; in horarios every row both screens
read (atenciones, objetos perdidos, reportes de turno) is already readable with
fn_puede_ver, so a narrower gate here would hide nothing. The rules live in
`app.services.asignacion.tablero`.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter

from app.db.asignacion import AsignacionDb
from app.services.asignacion import tablero as servicio
from app.services.asignacion.sql import Permission, require

router = APIRouter()


@router.get("/tablero-laboratorios")
def tablero_laboratorios(db: AsignacionDb) -> list[dict[str, Any]]:
    """One card per lab: semaforo, PC counts and the last attention."""
    require(db, Permission.VER)
    return servicio.tablero(db)


@router.get("/timeline")
def timeline(db: AsignacionDb, fecha: date | None = None) -> dict[str, Any]:
    """Attentions, shift reports and their decisions, done tasks, novedades and
    lost objects of one La Paz day."""
    require(db, Permission.VER)
    return servicio.timeline(db, fecha)
