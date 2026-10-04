"""Laboratorios views (Fase 3): thin Django layer over FastAPI /api/laboratorios/*."""

import contextlib
import datetime as _dt
import json
import logging

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .api import TIMEOUT, ApiError, api_delete, api_get, api_post, api_put
from .auth import con_login

_log = logging.getLogger(__name__)

TURNOS = ["mañana", "mediodia", "tarde", "noche"]

MEDIOS = ["Presencial", "WhatsApp"]


def _rol(request: HttpRequest) -> str:
    usuario = request.session.get("usuario") or {}
    return str(usuario.get("role", ""))


def _puede_reportes(request: HttpRequest) -> bool:
    usuario = request.session.get("usuario") or {}
    return _rol(request) == "Jefe" or bool(usuario.get("can_view_dashboard"))


def _es_encargado(request: HttpRequest) -> bool:
    usuario = request.session.get("usuario") or {}
    return str(usuario.get("role", "")) == "Encargado"


def _hoy_iso() -> str:
    return _dt.datetime.now(_dt.UTC).date().isoformat()


def _flash(request: HttpRequest, tipo: str, texto: str) -> None:
    request.session["flash"] = {"tipo": tipo, "texto": texto}


def _cards(token: str) -> dict[str, list[dict[str, object]]]:
    data = api_get("/api/laboratorios/cards", token)
    if not isinstance(data, dict):
        return {"activas": [], "inactivas": []}
    activas = data.get("activas")
    inactivas = data.get("inactivas")
    return {
        "activas": [c for c in activas if isinstance(c, dict)]
        if isinstance(activas, list)
        else [],
        "inactivas": [c for c in inactivas if isinstance(c, dict)]
        if isinstance(inactivas, list)
        else [],
    }


def _categorias(token: str) -> list[dict[str, object]]:
    data = api_get("/api/laboratorios/categorias", token)
    return [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []


def _norm_nombre(nombre: object) -> str:
    import unicodedata

    texto = unicodedata.normalize("NFD", str(nombre or "").strip().casefold())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _sugerencias_por_turno(token: str) -> dict[str, list[str]]:
    """Auxiliar names per turno for the datalist filter. Empty on API failure."""
    try:
        equipo = api_get("/api/laboratorios/equipo", token)
        horarios = api_get("/api/laboratorios/horarios", token)
    except ApiError:
        return {}
    if not isinstance(equipo, dict) or not isinstance(horarios, dict):
        return {}
    miembros = equipo.get("auxiliares")
    nombres = (
        {_norm_nombre(m.get("nombre", "")) for m in miembros if isinstance(m, dict)}
        if isinstance(miembros, list)
        else set()
    )
    salida: dict[str, list[str]] = {}
    for turno in TURNOS:
        bloque = horarios.get(turno)
        if not isinstance(bloque, dict):
            continue
        aux = bloque.get("auxiliares")
        lista = [str(n) for n in aux if isinstance(n, str) and _norm_nombre(n) in nombres] if isinstance(aux, list) else []
        salida[turno] = sorted(lista)
    return salida


def _turno_o_none(valor: object) -> str | None:
    texto = str(valor or "").strip()
    return texto if texto in TURNOS else None


def _medio_o_default(valor: object) -> str:
    texto = str(valor or "").strip()
    return texto if texto in MEDIOS else "Presencial"


def _combinar_auxiliares(primero: object, extras: object) -> str:
    vistos: list[str] = []
    candidatos = [primero] + (
        list(extras) if isinstance(extras, (list, tuple)) else [extras]
    )
    for c in candidatos:
        nombre = str(c or "").strip()
        if nombre and nombre.lower() not in [v.lower() for v in vistos]:
            vistos.append(nombre)
    return " + ".join(vistos)


@con_login
def lab_lista_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    lab_sel = request.GET.get("laboratorio_id", "").strip()
    cards = _cards(token)
    params = {"laboratorio_id": lab_sel} if lab_sel else None
    data = api_get("/api/laboratorios/atenciones", token, params)
    filas = [a for a in data if isinstance(a, dict)] if isinstance(data, list) else []
    return render(
        request,
        "atenciones/laboratorios_lista.html",
        {
            "activas": cards["activas"],
            "inactivas": cards["inactivas"],
            "atenciones": filas,
            "total": len(filas),
            "flash": request.session.pop("flash", None),
            "lab_sel": lab_sel,
        },
    )


def _item_lab_desde_post(post: dict[str, object]) -> tuple[dict[str, object] | None, str]:
    lab_id = str(post.get("laboratorio_id", "")).strip()
    categoria = str(post.get("categoria", "")).strip()
    descripcion = str(post.get("descripcion", "")).strip()
    solucion = str(post.get("solucion", "")).strip()
    if not lab_id:
        return None, "Elige un laboratorio."
    if not categoria:
        return None, "Elige una categoría."
    if not descripcion or not solucion:
        return None, "Faltan descripción o solución."
    try:
        lab_id_int = int(lab_id)
    except ValueError:
        return None, "Laboratorio inválido."
    _getlist = getattr(post, "getlist", None)
    extras = (
        _getlist("auxiliar_extra")
        if callable(_getlist)
        else post.get("auxiliar_extra", [])
    )
    return {
        "laboratorio_id": lab_id_int,
        "categoria": categoria,
        "auxiliar_nombre": _combinar_auxiliares(
            post.get("auxiliar_nombre", ""),
            extras,
        ),
        "turno": _turno_o_none(post.get("turno")),
        "medio_solicitud": _medio_o_default(post.get("medio_solicitud")),
        "descripcion": descripcion,
        "solucion": solucion,
        "observaciones": post.get("observaciones") or None,
        "fecha_registro": str(post.get("fecha_registro") or _hoy_iso()),
    }, ""


@con_login
def lab_nueva_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    error = ""
    batch: list[dict[str, object]] = request.session.get("lab_batch", [])
    edit_idx = request.session.get("lab_edit_idx")
    if edit_idx is not None and not (0 <= edit_idx < len(batch)):
        edit_idx = None
        request.session.pop("lab_edit_idx", None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "agregar":
            item, error = _item_lab_desde_post(request.POST)
            if not error and item is not None:
                if edit_idx is not None:
                    batch[edit_idx] = item
                    request.session.pop("lab_edit_idx", None)
                    edit_idx = None
                else:
                    batch.append(item)
                request.session["lab_batch"] = batch
                return redirect("lab_nueva")
            if edit_idx is not None and not error:
                request.session["lab_batch"] = batch
                return redirect("lab_nueva")
        elif action == "editar":
            try:
                idx = int(request.POST.get("idx", "-1"))
                _ = batch[idx]
            except (IndexError, ValueError):
                error = "Índice inválido."
            else:
                request.session["lab_edit_idx"] = idx
                return redirect("lab_nueva")
        elif action == "cancelar_edicion":
            request.session.pop("lab_edit_idx", None)
            return redirect("lab_nueva")
        elif action == "quitar":
            try:
                batch.pop(int(request.POST.get("idx", "-1")))
            except (IndexError, ValueError):
                error = "Índice inválido."
            request.session.pop("lab_edit_idx", None)
            edit_idx = None
            request.session["lab_batch"] = batch
            return redirect("lab_nueva")
        elif action == "enviar":
            a_enviar = batch
            if not a_enviar and edit_idx is None:
                directo, error = _item_lab_desde_post(request.POST)
                if directo is not None:
                    a_enviar = [directo]
            if not a_enviar:
                if not error:
                    error = "Lista vacía."
            else:
                for item in a_enviar:
                    try:
                        api_post("/api/laboratorios/atenciones", token, item)
                    except ApiError as e:
                        error = str(e.detail) if e.detail else "No se pudo enviar"
                        break
                else:
                    request.session["lab_batch"] = []
                    request.session.pop("lab_edit_idx", None)
                    _flash(request, "ok", f"{len(a_enviar)} atención(es) de laboratorio registrada(s)")
                    return redirect("lab_lista")
        else:
            error = error or "No se recibió la acción. Recargá y reintentá."
    cards = _cards(token)
    edit_item = batch[edit_idx] if edit_idx is not None else None
    aux1, aux_extras = "", []
    if isinstance(edit_item, dict):
        _partes = [
            p.strip()
            for p in str(edit_item.get("auxiliar_nombre", "")).split("+")
        ]
        _partes = [p for p in _partes if p]
        aux1 = _partes[0] if _partes else ""
        aux_extras = _partes[1:]
    return render(
        request,
        "atenciones/laboratorios_nueva.html",
        {
            "activas": cards["activas"],
            "inactivas": cards["inactivas"],
            "categorias": _categorias(token),
            "batch": batch,
            "error": error,
            "hoy": _hoy_iso(),
            "edit_item": edit_item,
            "aux1": aux1,
            "aux_extras": aux_extras,
            "edit_idx": edit_idx,
            "turnos": TURNOS,
            "medios": MEDIOS,
            "sugerencias_json": json.dumps(_sugerencias_por_turno(token)),
        },
    )


def _cuerpo_lab_edicion(request: HttpRequest) -> dict[str, object]:
    cuerpo: dict[str, object] = {
        "categoria": request.POST.get("categoria", ""),
        "auxiliar_nombre": request.POST.get("auxiliar_nombre", ""),
        "descripcion": request.POST.get("descripcion", ""),
        "solucion": request.POST.get("solucion", ""),
        "observaciones": request.POST.get("observaciones", ""),
        "fecha_registro": request.POST.get("fecha_registro", ""),
    }
    turno = _turno_o_none(request.POST.get("turno"))
    if turno is not None:
        cuerpo["turno"] = turno
    cuerpo["medio_solicitud"] = _medio_o_default(request.POST.get("medio_solicitud"))
    lab_id = request.POST.get("laboratorio_id", "").strip()
    if lab_id:
        with contextlib.suppress(ValueError):
            cuerpo["laboratorio_id"] = int(lab_id)
    return {k: v for k, v in cuerpo.items() if v != ""}


@con_login
def lab_editar_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("lab_lista")
    try:
        api_put(
            f"/api/laboratorios/atenciones/{atencion_id}",
            str(request.session["jwt"]),
            _cuerpo_lab_edicion(request),
        )
    except ApiError as e:
        _flash(request, "error", str(e.detail) if e.detail else "No se pudo guardar")
    else:
        _flash(request, "ok", f"Atención de laboratorio #{atencion_id} actualizada")
    return redirect("lab_lista")


@con_login
def lab_ticket_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    token = str(request.session["jwt"])
    usuario = request.session["usuario"]
    try:
        a = api_get(f"/api/laboratorios/atenciones/{atencion_id}", token)
    except ApiError:
        return render(request, "atenciones/_lab_ticket.html", {"a": None})
    if not isinstance(a, dict):
        return render(request, "atenciones/_lab_ticket.html", {"a": None})
    es_dueno = a.get("usuario_id") == usuario.get("id")
    return render(
        request,
        "atenciones/_lab_ticket.html",
        {
            "a": a,
            "puede_editar": es_dueno,
            "puede_eliminar": es_dueno,
        },
    )


@con_login
def lab_eliminar_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("lab_lista")
    try:
        api_delete(
            f"/api/laboratorios/atenciones/{atencion_id}", str(request.session["jwt"])
        )
    except ApiError as e:
        _flash(request, "error", str(e.detail) if e.detail else "No se pudo eliminar")
    else:
        _flash(request, "ok", f"Atención de laboratorio #{atencion_id} eliminada")
    return redirect("lab_lista")


def _params_lab(request: HttpRequest) -> dict[str, str]:
    params: dict[str, str] = {}
    lab = request.GET.get("laboratorio_id", "").strip()
    if lab:
        params["laboratorio_id"] = lab
    turno = request.GET.get("turno", "").strip()
    if turno in TURNOS:
        params["turno"] = turno
    for clave in ("desde", "hasta"):
        valor = request.GET.get(clave, "").strip()
        if len(valor) == 7 and valor[4] == "-":
            params[f"{clave}_ym"] = valor
    return params


@con_login
def lab_reportes_vista(request: HttpRequest) -> HttpResponse:
    if not (_puede_reportes(request) or _es_encargado(request)):
        return redirect("lab_lista")
    token = str(request.session["jwt"])
    params = _params_lab(request)
    try:
        stats = api_get("/api/laboratorios/stats", token, params)
    except ApiError as e:
        if e.status in (401, 403):
            raise
        _log.error("LAB-REP stats fallo: %s", e.detail)
        return render(
            request,
            "atenciones/laboratorios_reportes.html",
            {"error": True, "stats": None, "csv_url": ""},
            status=502,
        )
    stats = stats if isinstance(stats, dict) else {}
    cards = _cards(token)
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    csv_url = reverse("lab_export_csv") + (f"?{qs}" if qs else "")
    return render(
        request,
        "atenciones/laboratorios_reportes.html",
        {
            "error": False,
            "stats": stats,
            "activas": cards["activas"],
            "filtros": {
                "laboratorio_id": params.get("laboratorio_id", ""),
                "desde": params.get("desde_ym", ""),
                "hasta": params.get("hasta_ym", ""),
                "turno": params.get("turno", ""),
            },
            "turnos": TURNOS,
            "csv_url": csv_url,
        },
    )


def _par(labels_values: list[tuple[str, int]]) -> dict[str, list]:
    return {
        "labels": [l for l, _ in labels_values],
        "values": [v for _, v in labels_values],
    }


def _payload_lab_dashboard(
    stats: dict, anio_stats: dict | None = None
) -> dict[str, dict[str, dict[str, list]]]:
    """ECharts payload from existing /api/laboratorios/stats data (no new backend)."""
    por_mes = anio_stats.get("por_mes") if isinstance(anio_stats, dict) else None
    if not por_mes:
        por_mes = stats.get("por_mes") or []
    evolucion = _par(
        [
            (f"{p.get('anio')}-{int(p.get('mes', 0)):02d}", int(p.get("total", 0)))
            for p in por_mes
            if isinstance(p, dict)
        ]
    )
    por_lab = stats.get("por_lab") or []
    barras_lab = _par(
        [
            (str(p.get("laboratorio", "")), int(p.get("total", 0)))
            for p in por_lab
            if isinstance(p, dict)
        ]
    )
    por_cat = stats.get("por_categoria") or []
    dona_cat = _par(
        [
            (str(p.get("categoria", "")), int(p.get("total", 0)))
            for p in por_cat
            if isinstance(p, dict)
        ]
    )
    por_turno = stats.get("por_turno") or []
    barras_turno = _par(
        [
            (str(p.get("turno", "") or "—"), int(p.get("total", 0)))
            for p in por_turno
            if isinstance(p, dict)
        ]
    )
    return {
        "charts": {
            "evolucion": evolucion,
            "por_lab": barras_lab,
            "por_categoria": dona_cat,
            "por_turno": barras_turno,
        }
    }


@con_login
def lab_dashboard_vista(request: HttpRequest) -> HttpResponse:
    if not (_puede_reportes(request) or _es_encargado(request)):
        return redirect("lab_lista")
    token = str(request.session["jwt"])
    mes = request.GET.get("mes", "").strip()
    if len(mes) != 7 or mes[4] != "-":
        mes = _dt.datetime.now(_dt.UTC).strftime("%Y-%m")
    params = {"desde_ym": mes, "hasta_ym": mes}
    try:
        stats = api_get("/api/laboratorios/stats", token, params)
        atenciones = api_get("/api/laboratorios/atenciones", token)
    except ApiError as e:
        if e.status in (401, 403):
            raise
        _log.error("LAB-DASH fallo: %s", e.detail)
        return render(
            request,
            "atenciones/laboratorios_dashboard.html",
            {"error": True, "mes": mes},
            status=502,
        )
    stats = stats if isinstance(stats, dict) else {}
    anio = mes[:4]
    try:
        anio_stats = api_get(
            "/api/laboratorios/stats",
            token,
            {"desde_ym": f"{anio}-01", "hasta_ym": mes},
        )
    except ApiError:
        anio_stats = None
    anio_stats = anio_stats if isinstance(anio_stats, dict) else None
    filas = (
        [a for a in atenciones if isinstance(a, dict)]
        if isinstance(atenciones, list)
        else []
    )
    # /atenciones has no date filter — narrow to the month client-side.
    mes_filas = [a for a in filas if str(a.get("fecha_registro", ""))[:7] == mes]
    por_lab = stats.get("por_lab") or []
    por_turno = stats.get("por_turno") or []
    lab_top = por_lab[0] if isinstance(por_lab, list) and por_lab else None
    turno_top = por_turno[0] if isinstance(por_turno, list) and por_turno else None
    auxiliares = {str(a.get("auxiliar_nombre", "")).strip() for a in mes_filas}
    auxiliares.discard("")
    # Per-lab breakdown (top categoria / top turno) derived from rows:
    # backend stats has no per-lab x categoria split — do NOT extend backend.
    detalle: dict[str, list[dict[str, object]]] = {}
    for a in mes_filas:
        detalle.setdefault(str(a.get("laboratorio", "") or "—"), []).append(a)
    por_lab_tabla = []
    for lab, rows in sorted(detalle.items(), key=lambda kv: len(kv[1]), reverse=True):
        cats: dict[str, int] = {}
        turnos: dict[str, int] = {}
        for a in rows:
            cat = str(a.get("categoria", "") or "—")
            tur = str(a.get("turno", "") or "—")
            cats[cat] = cats.get(cat, 0) + 1
            turnos[tur] = turnos.get(tur, 0) + 1
        por_lab_tabla.append(
            {
                "laboratorio": lab,
                "total": len(rows),
                "top_categoria": max(cats, key=cats.get) if cats else "—",
                "top_turno": max(turnos, key=turnos.get) if turnos else "—",
            }
        )
    return render(
        request,
        "atenciones/laboratorios_dashboard.html",
        {
            "error": False,
            "mes": mes,
            "kpis": {
                "total_mes": stats.get("total", 0),
                "lab_top": (lab_top or {}).get("laboratorio", "—")
                if isinstance(lab_top, dict)
                else "—",
                "lab_top_total": (lab_top or {}).get("total", 0)
                if isinstance(lab_top, dict)
                else 0,
                "turno_top": (turno_top or {}).get("turno", "—")
                if isinstance(turno_top, dict)
                else "—",
                "auxiliares_activos": len(auxiliares),
            },
            "por_lab_tabla": por_lab_tabla,
            "recientes": mes_filas[:10],
            "payload": _payload_lab_dashboard(stats, anio_stats),
        },
    )


@con_login
def lab_export_csv_vista(request: HttpRequest) -> HttpResponse:
    if not (_puede_reportes(request) or _es_encargado(request)):
        return redirect("lab_lista")
    token = str(request.session["jwt"])
    res = requests.get(
        settings.FASTAPI_URL + "/api/laboratorios/export.csv",
        headers={"Authorization": f"Bearer {token}"},
        params=_params_lab(request),
        timeout=TIMEOUT,
    )
    if res.status_code in (401, 403):
        return redirect("login")
    if res.status_code >= 400:
        _flash(request, "error", "No se pudo exportar el CSV")
        return redirect("lab_reportes")
    resp = HttpResponse(res.text, content_type="text/csv")
    resp["Content-Disposition"] = "attachment; filename=lab_atenciones.csv"
    return resp
