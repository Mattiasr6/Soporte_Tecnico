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


# ---------------------------------------------------------------- dashboard

TOP_HEATMAP = 6
TOP_PARETO = 8


def mes_etiqueta(anio: int, mes: int) -> str:
    return f"{anio}-{mes:02d}"


def mes_corto(anio: int, mes: int) -> str:
    return f"{MESES_CORTOS[mes - 1]} {anio}"


def graficos(stats: Stats) -> dict[str, Any]:
    """Every dashboard chart series, as Django `_graficos`."""
    por_categoria = sorted(
        stats.get("por_categoria") or [], key=lambda c: -_int(c["total"])
    )
    total = _int(stats.get("total"))

    acumulado: list[float] = []
    corrido = 0
    for c in por_categoria:
        corrido += _int(c["total"])
        acumulado.append(round(corrido * 100 / total, 1) if total else 0.0)

    cat_mes = list(stats.get("por_categoria_mes") or [])
    top_cats = [c["categoria"] for c in por_categoria[:TOP_HEATMAP]]
    meses = sorted({(_int(m["anio"]), _int(m["mes"])) for m in cat_mes})
    indices = {c: i for i, c in enumerate(top_cats)}
    indice_mes = {m: i for i, m in enumerate(meses)}
    celdas = [
        [
            indice_mes[(_int(m["anio"]), _int(m["mes"]))],
            indices[m["categoria"]],
            _int(m["total"]),
        ]
        for m in cat_mes
        if m["categoria"] in indices
    ]

    por_dia = list(stats.get("por_dia") or [])
    calendario = {
        "inicio": str(por_dia[0]["fecha"]) if por_dia else None,
        "fin": str(por_dia[-1]["fecha"]) if por_dia else None,
        "datos": [[str(d["fecha"]), _int(d["total"])] for d in por_dia],
        "max": max((_int(d["total"]) for d in por_dia), default=0),
    }

    # Two-step flow: channel -> category -> sector (same link sums as Django)
    enlaces: dict[tuple[str, str], int] = {}
    for fl in stats.get("flujo_sankey") or []:
        for origen, destino in (
            (fl["medio"], fl["categoria"]),
            (fl["categoria"], fl["grupo_padre"]),
        ):
            clave = (str(origen), str(destino))
            enlaces[clave] = enlaces.get(clave, 0) + _int(fl["total"])
    sankey = {
        "nodos": [{"name": n} for n in sorted({k for par in enlaces for k in par})],
        "links": [
            {"source": o, "target": d, "value": v} for (o, d), v in enlaces.items()
        ],
    }

    scatter = {
        "datos": [
            [
                _int(t["total"]),
                _int(t["fuera"]),
                str(t["display_name"]),
                round(_int(t["fuera"]) * 100 / _int(t["total"]), 1)
                if t["total"]
                else 0.0,
            ]
            for t in stats.get("por_tecnico_fuera") or []
        ]
    }

    ejes = [c["categoria"] for c in por_categoria]
    por_tec: dict[tuple[int, str], dict[str, int]] = {}
    for t in stats.get("por_tecnico_categoria") or []:
        clave_tec = (_int(t["usuario_id"]), str(t["display_name"]))
        por_tec.setdefault(clave_tec, {})[str(t["categoria"])] = _int(t["total"])
    radar = {
        "ejes": ejes,
        "tecnicos": [
            {
                "id": k[0],
                "nombre": k[1],
                "valores": [v.get(c, 0) for c in ejes],
                "total": sum(v.values()),
            }
            for k, v in sorted(por_tec.items(), key=lambda kv: -sum(kv[1].values()))
        ],
    }

    def _pares(filas: Iterable[dict[str, Any]], clave: str) -> dict[str, list[Any]]:
        lista = list(filas)
        return {
            "labels": [f[clave] for f in lista],
            "values": [_int(f["total"]) for f in lista],
        }

    por_mes = list(stats.get("por_mes") or [])
    return {
        "total": total,
        "fuera_de_turno": _int(stats.get("fuera_de_turno")),
        "arbol_conteos": {
            "padres": stats.get("por_padre") or [],
            "grupos": stats.get("por_grupo") or [],
            "areas": stats.get("por_area_id") or [],
        },
        "calendario": calendario,
        "sankey": sankey,
        "scatter": scatter,
        "radar": radar,
        "categoria": _pares(por_categoria, "categoria"),
        "pareto": {
            "labels": [c["categoria"] for c in por_categoria[:TOP_PARETO]],
            "values": [_int(c["total"]) for c in por_categoria[:TOP_PARETO]],
            "acumulado": acumulado[:TOP_PARETO],
        },
        "categoria_mes": {
            "categorias": top_cats,
            "meses": [mes_etiqueta(a, m) for a, m in meses],
            "celdas": celdas,
            "max": max((c[2] for c in celdas), default=0),
        },
        "rendimiento": _pares(stats.get("por_tecnico") or [], "display_name"),
        "colaboraciones": _pares(stats.get("asistencias") or [], "display_name"),
        "evolucion": {
            "labels": [mes_etiqueta(_int(m["anio"]), _int(m["mes"])) for m in por_mes],
            "values": [_int(m["total"]) for m in por_mes],
        },
        "medio": _pares(stats.get("por_medio") or [], "medio"),
        "tipo_solicitante": _pares(stats.get("por_tipo_solicitante") or [], "tipo"),
        "top_areas": list(stats.get("por_area") or [])[:10],
    }


def ficha(
    stats: Stats, scope: dict[str, str], padre: dict[str, int] | None
) -> dict[str, Any]:
    """Summary card of the current filter, as Django `_ficha`.

    `padre` holds total / fuera_de_turno of the sector alone when a dependency
    or area is selected, to compare the share and the after-hours rate.
    """
    total = _int(stats.get("total"))
    fuera = _int(stats.get("fuera_de_turno"))
    meses = [m for m in stats.get("por_mes") or [] if _int(m["total"]) > 0]
    pico = max(meses, key=lambda m: _int(m["total"]), default=None)
    valle = min(meses, key=lambda m: _int(m["total"]), default=None)
    cats = sorted(stats.get("por_categoria") or [], key=lambda c: -_int(c["total"]))
    top3 = sum(_int(c["total"]) for c in cats[:3])
    fuera_pct = round(fuera * 100 / total, 1) if total else 0.0
    pct_padre = delta_padre = None
    if padre is not None:
        ptotal = _int(padre.get("total"))
        if ptotal:
            pct_padre = round(total * 100 / ptotal, 1)
            pfuera = _int(padre.get("fuera_de_turno"))
            delta_padre = round(fuera_pct - (pfuera * 100 / ptotal), 1)
    padres = list(stats.get("por_padre") or [])
    nombre_padre = (
        str(padres[0]["nombre"])
        if scope.get("grupo_padre_id") and len(padres) == 1
        else None
    )
    return {
        "casos": total,
        "nombre_padre": nombre_padre,
        "fuera": fuera,
        "fuera_pct": fuera_pct,
        "promedio_mes": round(total / len(meses), 1) if meses else 0,
        "meses_activos": len(meses),
        "pico": mes_corto(_int(pico["anio"]), _int(pico["mes"])) if pico else None,
        "pico_total": _int(pico["total"]) if pico else 0,
        "valle": mes_corto(_int(valle["anio"]), _int(valle["mes"])) if valle else None,
        "valle_total": _int(valle["total"]) if valle else 0,
        "dominante": cats[0]["categoria"] if cats else None,
        "dominante_pct": round(_int(cats[0]["total"]) * 100 / total, 1)
        if cats and total
        else 0.0,
        "top3_pct": round(top3 * 100 / total, 1) if total else 0.0,
        "pct_padre": pct_padre,
        "delta_padre": delta_padre,
        "scope": scope,
    }


def mes_valido(valor: str | None) -> tuple[int, int] | None:
    """(year, month) of a "YYYY-MM" filter; anything else is ignored (as Django)."""
    v = (valor or "").strip()
    if len(v) == 7 and v[4] == "-" and v[:4].isdigit() and v[5:].isdigit():
        anio, mes = int(v[:4]), int(v[5:])
        if 1 <= mes <= 12:
            return anio, mes
    return None
