"""Software inventory (ported from the Soporte `routers/software.py`).

A lab's software list is replaced as a whole (Django "Guardar en este lab").
Marking the state of one software on one PC also records a `programas`
attention on that PC, like Django recorded a LabAtencion with "<software>
<verbo> <pc>" and a fixed solution. The attention goes through the normal
atenciones triggers: it takes the turno of the moment and is refused on a PC
that is not operativa (only correctivo is allowed there), which rolls the state
change back too.
"""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.asignacion_software import AmbienteSoftwareIn, SoftwareIn
from app.services.asignacion.sql import error_detail, not_found, rows, writing

# Django ACCION_TEXTO: estado -> (verb in the description, solution text).
ACCION_TEXTO = {
    "instalado": ("instalado en", "Instalación verificada en sala"),
    "falta": ("falta en", "Pendiente de instalación"),
    "dañado": ("dañado en", "Pendiente de revisión"),
}

_SOFTWARE = """
    select s.id, s.nombre, s.licencia, s.uso, s.esencial, s.docentes, s.activo,
           coalesce(array(select a.ambiente_id from horarios.ambiente_software a
                           where a.software_id = s.id order by a.ambiente_id),
                    '{}') as ambientes
      from horarios.software s
"""


def _422(message: str) -> HTTPException:
    return HTTPException(422, error_detail(message, None))


def listar(db: Session) -> list[dict[str, Any]]:
    return [dict(r) for r in rows(db, text(f"{_SOFTWARE} order by lower(s.nombre)"))]


def uno(db: Session, software_id: int) -> dict[str, Any]:
    found = rows(db, text(f"{_SOFTWARE} where s.id = :id"), {"id": software_id})
    if not found:
        raise not_found()
    return dict(found[0])


def _valores(body: SoftwareIn) -> dict[str, Any]:
    return {**body.model_dump(), "nombre": body.nombre.strip(), "uso": body.uso.strip()}


def crear(db: Session, body: SoftwareIn) -> dict[str, Any]:
    sql = text(
        """
        insert into horarios.software (nombre, licencia, uso, esencial, docentes, activo)
        values (:nombre, :licencia, :uso, :esencial, :docentes, :activo)
        returning id
        """
    )
    with writing(db):
        software_id = db.execute(sql, _valores(body)).scalar_one()
    return uno(db, software_id)


def editar(db: Session, software_id: int, body: SoftwareIn) -> dict[str, Any]:
    sql = text(
        """
        update horarios.software
           set nombre = :nombre, licencia = :licencia, uso = :uso,
               esencial = :esencial, docentes = :docentes, activo = :activo
         where id = :id
        returning id
        """
    )
    with writing(db):
        if db.execute(sql, {**_valores(body), "id": software_id}).first() is None:
            raise not_found()
    return uno(db, software_id)


def de_ambiente(db: Session, ambiente_id: int) -> list[dict[str, Any]]:
    if (
        db.execute(
            text("select 1 from horarios.ambientes where id = :id"), {"id": ambiente_id}
        ).first()
        is None
    ):
        raise not_found()
    sql = text(
        f"""
        {_SOFTWARE}
          join horarios.ambiente_software a2 on a2.software_id = s.id
         where a2.ambiente_id = :amb
         order by lower(s.nombre)
        """
    )
    return [dict(r) for r in rows(db, sql, {"amb": ambiente_id})]


def definir_de_ambiente(
    db: Session, ambiente_id: int, body: AmbienteSoftwareIn
) -> dict[str, Any]:
    """Replace the software list of a lab; PC states of removed ones go too."""
    ids = list(dict.fromkeys(body.software_ids))
    with writing(db):
        if (
            db.execute(
                text("select 1 from horarios.ambientes where id = :id for update"),
                {"id": ambiente_id},
            ).first()
            is None
        ):
            raise not_found()
        existentes = set(
            db.execute(
                text(
                    "select id from horarios.software where id = any(cast(:ids as bigint[]))"
                ),
                {"ids": ids},
            ).scalars()
        )
        faltan = [i for i in ids if i not in existentes]
        if faltan:
            raise _422(f"El software #{faltan[0]} no existe.")
        db.execute(
            text(
                "delete from horarios.ambiente_software"
                " where ambiente_id = :amb and not (software_id = any(cast(:ids as bigint[])))"
            ),
            {"amb": ambiente_id, "ids": ids},
        )
        db.execute(
            text(
                """
                insert into horarios.ambiente_software (ambiente_id, software_id)
                select :amb, unnest(cast(:ids as bigint[]))
                on conflict do nothing
                """
            ),
            {"amb": ambiente_id, "ids": ids},
        )
    return {"ambiente_id": ambiente_id, "software_ids": ids}


def _pc(db: Session, pc_id: int) -> Any:
    pc = db.execute(
        text(
            "select id, etiqueta, ambiente_id from horarios.ambiente_pcs where id = :id"
        ),
        {"id": pc_id},
    ).first()
    if pc is None:
        raise not_found()
    return pc


def de_pc(db: Session, pc_id: int) -> list[dict[str, Any]]:
    """Software of the PC's lab with its state on this PC ("falta" if never set)."""
    pc = _pc(db, pc_id)
    sql = text(
        """
        select s.id as software_id, s.nombre,
               coalesce(ps.estado, 'falta') as estado,
               ps.actualizado_en, p.nombre_completo as actualizado_por
          from horarios.ambiente_software a
          join horarios.software s on s.id = a.software_id
          left join horarios.pc_software ps
                 on ps.pc_id = :pc and ps.software_id = s.id
          left join horarios.perfiles p on p.id = ps.actualizado_por
         where a.ambiente_id = :amb
         order by lower(s.nombre)
        """
    )
    return [dict(r) for r in rows(db, sql, {"pc": pc_id, "amb": pc.ambiente_id})]


def marcar_en_pc(
    db: Session, pc_id: int, software_id: int, estado: str
) -> dict[str, Any]:
    """Set the state; a real change also records a `programas` attention."""
    with writing(db):
        pc = _pc(db, pc_id)
        sw = db.execute(
            text(
                """
                select s.id, s.nombre, ps.estado,
                       exists(select 1 from horarios.ambiente_software a
                               where a.ambiente_id = :amb and a.software_id = s.id)
                         as en_lab
                  from horarios.software s
                  left join horarios.pc_software ps
                         on ps.pc_id = :pc and ps.software_id = s.id
                 where s.id = :sw
                """
            ),
            {"sw": software_id, "pc": pc_id, "amb": pc.ambiente_id},
        ).first()
        if sw is None:
            raise _422("El software no existe.")
        if not sw.en_lab:
            raise _422(f"{sw.nombre} no está asignado al laboratorio de esta PC.")
        if sw.estado == estado:
            return {
                "software_id": sw.id,
                "nombre": sw.nombre,
                "estado": estado,
                "atencion_id": None,
            }
        db.execute(
            text(
                """
                insert into horarios.pc_software (pc_id, software_id, estado)
                values (:pc, :sw, :estado)
                on conflict (pc_id, software_id) do update
                   set estado = excluded.estado,
                       actualizado_por = horarios.fn_usuario_actual(),
                       actualizado_en = now()
                """
            ),
            {"pc": pc_id, "sw": sw.id, "estado": estado},
        )
        verbo, solucion = ACCION_TEXTO[estado]
        resuelto = estado == "instalado"
        atencion_id = db.execute(
            text(
                """
                insert into horarios.atenciones
                       (ambiente_id, pc_id, tipo, descripcion, solucion, estado,
                        resuelto_por, resuelto_en)
                values (:amb, :pc, 'programas', :descripcion, :solucion, :estado,
                        case when :resuelto then horarios.fn_usuario_actual() end,
                        case when :resuelto then now() end)
                returning id
                """
            ),
            {
                "amb": pc.ambiente_id,
                "pc": pc_id,
                "descripcion": f"{sw.nombre} {verbo} {pc.etiqueta}",
                "solucion": solucion,
                "estado": "resuelto" if resuelto else "pendiente",
                "resuelto": resuelto,
            },
        ).scalar_one()
    return {
        "software_id": sw.id,
        "nombre": sw.nombre,
        "estado": estado,
        "atencion_id": atencion_id,
    }


_PLANTILLA = """
    select id, nombre, tipo, descripcion, solucion, turno, activa
      from horarios.plantillas_atencion
"""


def plantillas(db: Session, solo_activas: bool) -> list[dict[str, Any]]:
    filtro = "where activa" if solo_activas else ""
    sql = text(f"{_PLANTILLA} {filtro} order by lower(nombre), id")
    return [dict(r) for r in rows(db, sql)]


def plantilla(db: Session, plantilla_id: int) -> dict[str, Any]:
    found = rows(db, text(f"{_PLANTILLA} where id = :id"), {"id": plantilla_id})
    if not found:
        raise not_found()
    return dict(found[0])
