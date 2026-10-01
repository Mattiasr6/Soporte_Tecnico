"""Laboratorios views (Fase 3): thin Django layer over FastAPI /api/laboratorios/*."""

import contextlib
import datetime as _dt
import logging

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .api import TIMEOUT, ApiError, api_delete, api_get, api_post, api_put
from .auth import con_login

_log = logging.getLogger(__name__)


def _rol(request: HttpRequest) -> str:
    usuario = request.session.get("usuario") or {}
    return str(usuario.get("role", ""))


def _puede_reportes(request: HttpRequest) -> bool:
    usuario = request.session.get("usuario") or {}
    return _rol(request) == "Jefe" or bool(usuario.get("can_view_dashboard"))


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


@con_login
def lab_lista_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    cards = _cards(token)
    data = api_get("/api/laboratorios/atenciones", token)
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
        },
    )


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
            lab_id = request.POST.get("laboratorio_id", "").strip()
            categoria = request.POST.get("categoria", "").strip()
            descripcion = request.POST.get("descripcion", "").strip()
            solucion = request.POST.get("solucion", "").strip()
            if not lab_id:
                error = "Elige un laboratorio."
            elif not categoria:
                error = "Elige una categoría."
            elif not descripcion or not solucion:
                error = "Faltan descripción o solución."
            else:
                try:
                    lab_id_int = int(lab_id)
                except ValueError:
                    error = "Laboratorio inválido."
                else:
                    item = {
                        "laboratorio_id": lab_id_int,
                        "categoria": categoria,
                        "auxiliar_nombre": request.POST.get("auxiliar_nombre", "").strip(),
                        "descripcion": descripcion,
                        "solucion": solucion,
                        "observaciones": request.POST.get("observaciones") or None,
                        "fecha_registro": request.POST.get("fecha_registro")
                        or _hoy_iso(),
                    }
                    if edit_idx is not None:
                        batch[edit_idx] = item
                        request.session.pop("lab_edit_idx", None)
                        edit_idx = None
                    else:
                        batch.append(item)
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
            if not batch:
                error = "Lista vacía."
            else:
                for item in batch:
                    try:
                        api_post("/api/laboratorios/atenciones", token, item)
                    except ApiError as e:
                        error = str(e.detail) if e.detail else "No se pudo enviar"
                        break
                else:
                    request.session["lab_batch"] = []
                    request.session.pop("lab_edit_idx", None)
                    _flash(request, "ok", f"{len(batch)} atención(es) de laboratorio registrada(s)")
                    return redirect("lab_lista")
    cards = _cards(token)
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
            "edit_item": batch[edit_idx] if edit_idx is not None else None,
            "edit_idx": edit_idx,
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
    for clave in ("desde", "hasta"):
        valor = request.GET.get(clave, "").strip()
        if len(valor) == 7 and valor[4] == "-":
            params[f"{clave}_ym"] = valor
    return params


@con_login
def lab_reportes_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_reportes(request):
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
            },
            "csv_url": csv_url,
        },
    )


@con_login
def lab_export_csv_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_reportes(request):
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
