"""Software inventory and lab attention templates (G7).

Ported from Django `auxiliares/software/` (catalogue, lab x software matrix,
templates) and the "Estados" panel of `auxiliares/laboratorios/<id>/pcs/`, which
used the Soporte `/api/software` router, onto the horarios tables of migration
0027. Logic lives in `app.services.asignacion.software`.

Permission mapping (Django -> horarios SQL helpers):
- every read (catalogue, a lab's software, a PC's states, templates):
  fn_puede_ver (Django: any logged-in user);
- catalogue create/edit/delete, a lab's software list, templates
  create/edit/delete: fn_puede_gestionar_auxiliares = admin (Jefe) and
  encargado (Django `_gestiona_equipo`: Jefe, dashboard viewers, Encargado);
- the state of a software on a PC: fn_puede_operar = admin, encargado, auxiliar,
  tecnico (Django: any user in the auxiliar roster).
Delete has no Django counterpart (it only deactivated); it is kept for
gestionar so mistakes can be removed.
"""

from typing import Any

from fastapi import APIRouter, Response

from app.db.asignacion import AsignacionDb
from app.schemas.asignacion_software import (
    AmbienteSoftwareIn,
    PcSoftwareIn,
    PlantillaAtencionIn,
    SoftwareIn,
)
from app.services.asignacion import software as servicio
from app.services.asignacion.sql import (
    Permission,
    delete_by_id,
    insert_returning_id,
    not_found,
    require,
    update_by_id,
    writing,
)

router = APIRouter()


# --- catalogue -------------------------------------------------------------------


@router.get("/software")
def listar_software(db: AsignacionDb) -> list[dict[str, Any]]:
    """Catalogue with the ids of the labs that have each software."""
    require(db, Permission.VER)
    return servicio.listar(db)


@router.post("/software", status_code=201)
def crear_software(body: SoftwareIn, db: AsignacionDb) -> dict[str, Any]:
    require(db, Permission.GESTIONAR_AUXILIARES)
    return servicio.crear(db, body)


@router.put("/software/{software_id}")
def editar_software(
    software_id: int, body: SoftwareIn, db: AsignacionDb
) -> dict[str, Any]:
    require(db, Permission.GESTIONAR_AUXILIARES)
    return servicio.editar(db, software_id, body)


@router.delete("/software/{software_id}", status_code=204)
def eliminar_software(software_id: int, db: AsignacionDb) -> Response:
    """Also removes it from every lab and PC (cascade)."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not delete_by_id(db, "software", software_id):
            raise not_found()
    return Response(status_code=204)


# --- lab x software --------------------------------------------------------------


@router.get("/ambientes/{ambiente_id}/software")
def software_de_ambiente(ambiente_id: int, db: AsignacionDb) -> list[dict[str, Any]]:
    require(db, Permission.VER)
    return servicio.de_ambiente(db, ambiente_id)


@router.put("/ambientes/{ambiente_id}/software")
def definir_software_de_ambiente(
    ambiente_id: int, body: AmbienteSoftwareIn, db: AsignacionDb
) -> dict[str, Any]:
    """Replace the whole software list of a lab."""
    require(db, Permission.GESTIONAR_AUXILIARES)
    return servicio.definir_de_ambiente(db, ambiente_id, body)


# --- per-PC state ----------------------------------------------------------------


@router.get("/ambiente-pcs/{pc_id}/software")
def software_de_pc(pc_id: int, db: AsignacionDb) -> list[dict[str, Any]]:
    require(db, Permission.VER)
    return servicio.de_pc(db, pc_id)


@router.put("/ambiente-pcs/{pc_id}/software/{software_id}")
def marcar_software_de_pc(
    pc_id: int, software_id: int, body: PcSoftwareIn, db: AsignacionDb
) -> dict[str, Any]:
    """Set instalado/falta/dañado; a change records a `programas` attention."""
    require(db, Permission.OPERAR)
    return servicio.marcar_en_pc(db, pc_id, software_id, body.estado)


# --- attention templates -----------------------------------------------------------


def _plantilla_valores(body: PlantillaAtencionIn) -> dict[str, Any]:
    return {
        **body.model_dump(),
        "nombre": body.nombre.strip(),
        "descripcion": body.descripcion.strip(),
        "solucion": body.solucion.strip(),
    }


@router.get("/plantillas-atencion")
def listar_plantillas(db: AsignacionDb, activas: bool = False) -> list[dict[str, Any]]:
    require(db, Permission.VER)
    return servicio.plantillas(db, activas)


@router.post("/plantillas-atencion", status_code=201)
def crear_plantilla(body: PlantillaAtencionIn, db: AsignacionDb) -> dict[str, Any]:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        plantilla_id = insert_returning_id(
            db, "plantillas_atencion", _plantilla_valores(body)
        )
    return servicio.plantilla(db, plantilla_id)


@router.put("/plantillas-atencion/{plantilla_id}")
def editar_plantilla(
    plantilla_id: int, body: PlantillaAtencionIn, db: AsignacionDb
) -> dict[str, Any]:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not update_by_id(
            db, "plantillas_atencion", plantilla_id, _plantilla_valores(body)
        ):
            raise not_found()
    return servicio.plantilla(db, plantilla_id)


@router.delete("/plantillas-atencion/{plantilla_id}", status_code=204)
def eliminar_plantilla(plantilla_id: int, db: AsignacionDb) -> Response:
    require(db, Permission.GESTIONAR_AUXILIARES)
    with writing(db):
        if not delete_by_id(db, "plantillas_atencion", plantilla_id):
            raise not_found()
    return Response(status_code=204)
