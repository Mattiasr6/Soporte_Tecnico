"""Soporte dashboard and monthly report computations.

Ported from the Django views (`frontend-django/atenciones/views.py`:
`_periodo_reporte`, `_kpis_reporte`, `_evolucion`, `_top_areas`, `_destacados`,
`_metodologia`, ...). They used to run in the Django process on top of
GET /api/atenciones/stats; now the API returns the finished payload so the
Angular screens only render it. Every function here is pure: it takes the
stats as a plain dict (`StatsOut.model_dump()`) and returns plain data.
"""

import calendar
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

MESES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)
MESES_CORTOS = tuple(m[:3].lower() for m in MESES)
VISTAS_REPORTE = ("mes", "anio")

Stats = dict[str, Any]


def _int(valor: object) -> int:
    return int(valor or 0)  # type: ignore[call-overload]


def dias_del_mes(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def mes_vecino(anio: int, mes: int, delta: int) -> tuple[int, int]:
    """(year, month) `delta` months away from the given one."""
    indice = anio * 12 + (mes - 1) + delta
    return indice // 12, indice % 12 + 1


def dias_habiles(anio: int, mes: int | None) -> int:
    """Monday-to-Saturday days of the month (or the whole year when mes is None)."""
    if mes is None:
        inicio, fin = date(anio, 1, 1), date(anio, 12, 31)
    else:
        inicio, fin = date(anio, mes, 1), date(anio, mes, dias_del_mes(anio, mes))
    n = 0
    d = inicio
    while d <= fin:
        if d.weekday() < 6:
            n += 1
        d += timedelta(days=1)
    return n


def rango_mes(anio: int, mes: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, dias_del_mes(anio, mes))


def rango_anio(anio: int, mes_fin: int) -> tuple[date, date]:
    """January 1st up to the last day of `mes_fin` (year-to-date view)."""
    return date(anio, 1, 1), date(anio, mes_fin, dias_del_mes(anio, mes_fin))


def periodo_reporte(mes: str | None, vista: str | None, hoy: date) -> dict[str, Any]:
    """Validated report period; invalid values fall back to the current month / "mes"."""
    vista = (vista or "mes").strip()
    if vista not in VISTAS_REPORTE:
        vista = "mes"
    crudo = (mes or "").strip()
    anio, num = hoy.year, hoy.month
    if (
        len(crudo) == 7
        and crudo[4] == "-"
        and crudo[:4].isdigit()
        and crudo[5:].isdigit()
        and 1 <= int(crudo[5:]) <= 12
    ):
        anio, num = int(crudo[:4]), int(crudo[5:])
    en_curso = (anio, num) == (hoy.year, hoy.month)
    etiqueta = (
        f"Acumulado enero\u2013{MESES[num - 1].lower()} {anio}"
        if vista == "anio"
        else f"{MESES[num - 1]} {anio}"
    )
    if en_curso:
        etiqueta = f"{etiqueta} (parcial)"
    return {
        "vista": vista,
        "mes": f"{anio}-{num:02d}",
        "anio": anio,
        "mes_num": num,
        "etiqueta": etiqueta,
        "es_mes_en_curso": en_curso,
    }


def orden_desc(filas: Iterable[object], clave: str) -> list[dict[str, Any]]:
    """Rows by total desc, then by `clave` (stable order for ties)."""
    return sorted(
        (f for f in filas if isinstance(f, dict)),
        key=lambda f: (-_int(f.get("total")), str(f.get(clave, ""))),
    )


def serie(filas: list[dict[str, Any]], clave: str) -> dict[str, list[Any]]:
    return {
        "labels": [str(f.get(clave, "")) for f in filas],
        "values": [_int(f.get("total")) for f in filas],
    }


def evolucion(stats: Stats, anio: int, mes_fin: int) -> dict[str, list[Any]]:
    """Attentions per month of `anio`, January to `mes_fin`, zero-filled."""
    por_mes = {
        _int(m.get("mes")): _int(m.get("total"))
        for m in stats.get("por_mes") or []
        if isinstance(m, dict) and _int(m.get("anio")) == anio
    }
    return {
        "labels": [MESES_CORTOS[m - 1] for m in range(1, mes_fin + 1)],
        "values": [por_mes.get(m, 0) for m in range(1, mes_fin + 1)],
    }


def top_areas(stats: Stats, total: int) -> list[dict[str, Any]]:
    filas = orden_desc(stats.get("por_area") or [], "area")[:10]
    return [
        {
            "area": str(f.get("area", "")),
            "total": _int(f.get("total")),
            "pct": round(_int(f.get("total")) * 100 / total, 1) if total else 0.0,
        }
        for f in filas
    ]


def kpis_reporte(
    s_mes: Stats, s_prev: Stats | None, s_evol: Stats, dias: int
) -> dict[str, Any]:
    total = _int(s_mes.get("total"))
    fuera = _int(s_mes.get("fuera_de_turno"))
    fuera_pct = round(fuera * 100 / total, 1) if total else 0.0
    prev_total = delta_abs = delta_pct = fuera_delta = None
    if s_prev is not None:
        prev_total = _int(s_prev.get("total"))
        delta_abs = total - prev_total
        if prev_total:
            delta_pct = round((total - prev_total) * 100 / prev_total, 1)
            prev_fuera = _int(s_prev.get("fuera_de_turno"))
            fuera_delta = round(fuera_pct - prev_fuera * 100 / prev_total, 1)
    return {
        "total": total,
        "prev_total": prev_total,
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "fuera_pct": fuera_pct,
        "fuera_delta_pts": fuera_delta,
        "promedio_dia": round(total / dias, 1) if dias else 0.0,
        "dias_periodo": dias,
        "areas_distintas": len(list(s_mes.get("por_area") or [])),
        "meses_activos": sum(
            1 for m in s_evol.get("por_mes") or [] if _int(m.get("total")) > 0
        ),
    }


def destacados(
    filas: Iterable[dict[str, Any]], categorias: list[str]
) -> list[dict[str, Any]]:
    """One featured case per category: the longest solution (lowest id on ties).

    `filas` are the attentions of the period (Django filtered its last 2000
    rows by month; the API queries the month directly).
    """
    lista = list(filas)
    salida: list[dict[str, Any]] = []
    for categoria in categorias:
        candidatos = [a for a in lista if a.get("categoria") == categoria]
        if not candidatos:
            continue
        mejor = max(
            candidatos,
            key=lambda a: (len(str(a.get("solucion") or "")), -_int(a.get("id"))),
        )
        salida.append(
            {
                "id": _int(mejor.get("id")),
                "area": str(mejor.get("area_solicitante") or ""),
                "categoria": str(mejor.get("categoria") or ""),
                "descripcion": str(mejor.get("descripcion") or ""),
                "solucion": str(mejor.get("solucion") or ""),
            }
        )
    return salida


def metodologia(periodo: dict[str, Any], ahora: datetime) -> dict[str, str]:
    """Source, covered dates and cut-off note printed under the report."""
    anio = int(periodo["anio"])
    mes = int(periodo["mes_num"])
    inicio = date(anio, 1, 1) if periodo["vista"] == "anio" else date(anio, mes, 1)
    fin = date(anio, mes, dias_del_mes(anio, mes))
    if periodo["es_mes_en_curso"]:
        corte = (
            f"Datos al {ahora.strftime('%d/%m/%Y')} — mes en curso, cifras parciales"
        )
    elif periodo["vista"] == "anio":
        corte = f"Acumulado enero\u2013{MESES[mes - 1].lower()} {anio}"
    else:
        corte = "Mes cerrado"
    return {
        "fuente": "GET /api/atenciones/reporte",
        "periodo": f"{inicio.strftime('%d/%m/%Y')}\u2013{fin.strftime('%d/%m/%Y')}",
        "generado_en": ahora.strftime("%d/%m/%Y %H:%M"),
        "corte": corte,
    }


def charts_reporte(
    principal: Stats, stats_evolucion: Stats, anio: int, mes: int
) -> dict[str, Any]:
    total = _int(principal.get("total"))
    categorias = orden_desc(principal.get("por_categoria") or [], "categoria")
    return {
        "evolucion": evolucion(stats_evolucion, anio, mes),
        "categoria": serie(categorias, "categoria"),
        "sectores": serie(
            orden_desc(principal.get("por_padre") or [], "nombre"), "nombre"
        ),
        "medio": serie(orden_desc(principal.get("por_medio") or [], "medio"), "medio"),
        "tipo_solicitante": serie(
            orden_desc(principal.get("por_tipo_solicitante") or [], "tipo"), "tipo"
        ),
        "top_areas": top_areas(principal, total),
    }
