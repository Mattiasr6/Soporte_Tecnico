"""Saturday planner (ported from Django `auxiliares_sabados_vista`).

A planned Saturday is a `horarios.sabados` row. Its auxiliares are
`rotacion_sabados` rows (one per auxiliar, with the turno) and a turno can have
its own hours that date (`sabado_horarios`); otherwise it uses
`horarios_turno`. Saving a date replaces its whole plan, and a date left with
nobody is cleared (Django deleted it the same way).
"""

import calendar
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.asignacion_turnos import SabadoIn
from app.services.asignacion.sql import error_detail, rows, writing

ZONA = ZoneInfo("America/La_Paz")
TURNOS_SABADO = ("M", "MD", "T")
# Shift order for turnos outside TURNOS_SABADO kept by old rows (N).
_ORDEN = {"M": 0, "MD": 1, "T": 2, "N": 3}


def hoy() -> date:
    return datetime.now(ZONA).date()


def sabados_del_mes(anio: int, mes: int) -> list[date]:
    dias = calendar.monthrange(anio, mes)[1]
    return [
        date(anio, mes, d)
        for d in range(1, dias + 1)
        if date(anio, mes, d).weekday() == calendar.SATURDAY
    ]


def horarios_base(db: Session) -> dict[str, tuple[time, time]]:
    """Default hours of every turno (`horarios_turno`)."""
    sql = text("select turno, hora_inicio, hora_fin from horarios.horarios_turno")
    return {r["turno"]: (r["hora_inicio"], r["hora_fin"]) for r in rows(db, sql)}


def _planes(db: Session, desde: date, hasta: date) -> dict[date, dict[str, Any]]:
    """Planned dates in [desde, hasta]: note, own hours and auxiliares by turno."""
    rango = {"desde": desde, "hasta": hasta}
    planes: dict[date, dict[str, Any]] = {}
    sql = (
        "select fecha, nota from horarios.sabados where fecha between :desde and :hasta"
    )
    for r in rows(db, text(sql), rango):
        planes[r["fecha"]] = {"nota": r["nota"], "horas": {}, "auxiliares": {}}
    sql = (
        "select fecha, turno, hora_inicio, hora_fin from horarios.sabado_horarios"
        " where fecha between :desde and :hasta"
    )
    for r in rows(db, text(sql), rango):
        planes[r["fecha"]]["horas"][r["turno"]] = (r["hora_inicio"], r["hora_fin"])
    sql = """
        select r.fecha, r.turno, p.id, p.nombre_completo
          from horarios.rotacion_sabados r
          join horarios.perfiles p on p.id = r.auxiliar_id
         where r.fecha between :desde and :hasta
         order by p.nombre_completo, p.id
    """
    for r in rows(db, text(sql), rango):
        lista = planes[r["fecha"]]["auxiliares"].setdefault(r["turno"], [])
        lista.append({"id": r["id"], "nombre_completo": r["nombre_completo"]})
    return planes


def _dia(
    fecha: date, plan: dict[str, Any] | None, base: dict[str, tuple[time, time]]
) -> dict[str, Any]:
    plan = plan or {"nota": None, "horas": {}, "auxiliares": {}}
    codigos = sorted(set(TURNOS_SABADO) | set(plan["auxiliares"]), key=_ORDEN.get)
    turnos = []
    for turno in codigos:
        propio = plan["horas"].get(turno)
        inicio, fin = propio or base.get(turno, (None, None))
        turnos.append(
            {
                "turno": turno,
                "hora_inicio": inicio,
                "hora_fin": fin,
                "personalizado": propio is not None,
                "auxiliares": plan["auxiliares"].get(turno, []),
            }
        )
    return {
        "fecha": fecha,
        "planificado": bool(plan["auxiliares"]),
        "nota": plan["nota"],
        "turnos": turnos,
    }


def mes(db: Session, anio: int, mes_: int) -> dict[str, Any]:
    """Every Saturday of the month (planned or not) and the default hours."""
    fechas = sabados_del_mes(anio, mes_)
    base = horarios_base(db)
    planes = _planes(db, fechas[0], fechas[-1])
    return {
        "anio": anio,
        "mes": mes_,
        "horarios": [
            {"turno": t, "hora_inicio": base[t][0], "hora_fin": base[t][1]}
            for t in TURNOS_SABADO
            if t in base
        ],
        "sabados": [_dia(f, planes.get(f), base) for f in fechas],
    }


def dia(db: Session, fecha: date) -> dict[str, Any]:
    return _dia(fecha, _planes(db, fecha, fecha).get(fecha), horarios_base(db))


def _error(mensaje: str) -> HTTPException:
    return HTTPException(422, error_detail(mensaje, None))


def guardar(db: Session, fecha: date, body: SabadoIn) -> dict[str, Any]:
    """Replace the plan of one Saturday; with no auxiliares the date is cleared."""
    if fecha.weekday() != calendar.SATURDAY:
        raise _error("La fecha elegida no es un sábado.")
    ids = [a for t in body.turnos for a in t.auxiliares]
    if ids:
        sql = text(
            "select id from horarios.perfiles where id = any(cast(:ids as uuid[]))"
        )
        existen = {r["id"] for r in rows(db, sql, {"ids": [str(i) for i in ids]})}
        if set(ids) - existen:
            raise _error("Uno de los auxiliares elegidos ya no existe.")
    if not ids:
        with writing(db):
            limpiar_fecha(db, fecha)
        return dia(db, fecha)

    base = horarios_base(db)
    nota = (body.nota or "").strip() or None
    with writing(db):
        db.execute(
            text(
                """
                insert into horarios.sabados (fecha, nota) values (:fecha, :nota)
                on conflict (fecha) do update
                   set nota = excluded.nota, actualizado_en = now()
                """
            ),
            {"fecha": fecha, "nota": nota},
        )
        for tabla in ("sabado_horarios", "rotacion_sabados"):
            db.execute(
                text(f"delete from horarios.{tabla} where fecha = :fecha"),
                {"fecha": fecha},
            )
        for t in body.turnos:
            horas = (t.hora_inicio, t.hora_fin)
            # Hours equal to the defaults are not an override.
            if t.hora_inicio and horas != base.get(t.turno):
                db.execute(
                    text(
                        "insert into horarios.sabado_horarios"
                        " (fecha, turno, hora_inicio, hora_fin)"
                        " values (:fecha, :turno, :inicio, :fin)"
                    ),
                    {
                        "fecha": fecha,
                        "turno": t.turno,
                        "inicio": horas[0],
                        "fin": horas[1],
                    },
                )
            for auxiliar in t.auxiliares:
                db.execute(
                    text(
                        "insert into horarios.rotacion_sabados (fecha, auxiliar_id, turno)"
                        " values (:fecha, :auxiliar, :turno)"
                    ),
                    {"fecha": fecha, "auxiliar": auxiliar, "turno": t.turno},
                )
    return dia(db, fecha)


def limpiar_fecha(db: Session, fecha: date) -> bool:
    """Delete a planned date (its auxiliares and hours cascade)."""
    sql = text("delete from horarios.sabados where fecha = :fecha returning 1")
    return db.execute(sql, {"fecha": fecha}).first() is not None
