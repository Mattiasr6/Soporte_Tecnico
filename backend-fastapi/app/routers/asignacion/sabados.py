"""Saturday planner and schedule export (Django `auxiliares/horarios-sabados/`
and `auxiliares/horarios/export.xlsx|.pdf`).

Permissions follow the rotacion_sabados RLS rules (99_rls_reference.sql):
read with fn_puede_ver, plan and clear with fn_puede_gestionar_auxiliares
(admin/encargado; Django: Jefe, dashboard viewers and Encargado). The rules
live in `app.services.asignacion.sabados`. The export (weekly shifts or the
Saturdays of a month) is readable with fn_puede_ver, like the Django one that
any logged-in user could download; it is built in `exportes`.
"""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_turnos import SabadoIn
from app.services.asignacion import exportes
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


Mes = Annotated[int | None, Query(ge=1, le=12)]
Anio = Annotated[int | None, Query(ge=2000, le=2100)]
TipoExport = Literal["semanal", "sabado"]


def _contenido(
    db: AsignacionDb, tipo: TipoExport, mes: int | None, anio: int | None
) -> tuple[str, list[str], list[exportes.Fila], str]:
    require(db, Permission.VER)
    if tipo == "semanal":
        return exportes.semanal(db)
    hoy = servicio.hoy()
    return exportes.sabado(db, anio or hoy.year, mes or hoy.month)


def _archivo(contenido: bytes, media: str, nombre: str) -> Response:
    return Response(
        content=contenido,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/horarios/export.xlsx")
def exportar_horarios_xlsx(
    db: AsignacionDb, tipo: TipoExport = "sabado", mes: Mes = None, anio: Anio = None
) -> Response:
    """Weekly shifts or the Saturdays of a month (default: this month) as XLSX."""
    titulo, cabecera, filas, nombre = _contenido(db, tipo, mes, anio)
    contenido = exportes.libro_xlsx(titulo, cabecera, filas)
    return _archivo(contenido, exportes.XLSX_MEDIA, f"{nombre}.xlsx")


@router.get("/horarios/export.pdf")
def exportar_horarios_pdf(
    db: AsignacionDb, tipo: TipoExport = "sabado", mes: Mes = None, anio: Anio = None
) -> Response:
    """Same content as the XLSX, as a landscape A4 PDF table."""
    titulo, cabecera, filas, nombre = _contenido(db, tipo, mes, anio)
    contenido = exportes.hoja_pdf(titulo, cabecera, filas)
    return _archivo(contenido, "application/pdf", f"{nombre}.pdf")
