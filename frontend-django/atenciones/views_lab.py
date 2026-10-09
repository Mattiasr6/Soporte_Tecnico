"""Laboratorios views (Fase 3): thin Django layer over FastAPI /api/laboratorios/*."""

import contextlib
import datetime as _dt
import json
import logging
from urllib.parse import quote

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .api import TIMEOUT, ApiError, api_delete, api_get, api_patch, api_post, api_put
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


def _items_lab_desde_post(post: dict[str, object]) -> tuple[list[dict[str, object]], str]:
    """Un item por cada laboratorio marcado en el form."""
    categoria = str(post.get("categoria", "")).strip()
    descripcion = str(post.get("descripcion", "")).strip()
    solucion = str(post.get("solucion", "")).strip()
    _getlist = getattr(post, "getlist", None)
    if callable(_getlist):
        labs = [v for v in _getlist("laboratorio_id") if str(v).strip()]
    else:
        bruto = post.get("laboratorio_id", "")
        lista = bruto if isinstance(bruto, list) else [bruto]
        labs = [v for v in lista if str(v).strip()]
    if not labs:
        return [], "Elegí al menos un laboratorio."
    if not categoria:
        return [], "Elegí una categoría."
    if not descripcion or not solucion:
        return [], "Faltan descripción o solución."
    try:
        labs_int = [int(v) for v in labs]
    except (TypeError, ValueError):
        return [], "Laboratorio inválido."
    extras = (
        _getlist("auxiliar_extra")
        if callable(_getlist)
        else post.get("auxiliar_extra", [])
    )
    import re as _re
    pc_norm = _re.sub(r"\s+", " ", str(post.get("pc_nombre") or "")).strip().upper() or None
    base = {
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
        "pc_nombre": pc_norm,
        "fecha_registro": str(post.get("fecha_registro") or _hoy_iso()),
    }
    return [{**base, "laboratorio_id": lab_id} for lab_id in labs_int], ""


AVISO_SIN_VINCULO = (
    "Tu cuenta no está vinculada a la nómina; pedile al Jefe que la vincule"
)


def _es_auxiliar(request: HttpRequest) -> bool:
    return _rol(request) in ("Auxiliar", "Encargado")


def cargar_identidad_auxiliar(request: HttpRequest) -> None:
    """Toma de la cuenta logueada su nombre de nómina (sin elegir "quién soy")."""
    request.session.pop("auxiliar_nombre", None)
    request.session.pop("auxiliar_encargado", None)
    if not _es_auxiliar(request):
        return
    try:
        datos = api_get("/api/laboratorios/equipo/yo", str(request.session["jwt"]))
    except (ApiError, requests.RequestException):
        return
    nombre = str(datos.get("nombre", "")).strip() if isinstance(datos, dict) else ""
    if nombre:
        request.session["auxiliar_nombre"] = nombre
        request.session["auxiliar_encargado"] = bool(datos.get("encargado", False))


def _sin_vinculo(request: HttpRequest) -> bool:
    """Auxiliar/Encargado cuya cuenta aún no está vinculada a la nómina.

    Reintenta una vez por request por si el Jefe la vinculó tras el login.
    """
    if not _es_auxiliar(request):
        return False
    if not (request.session.get("auxiliar_nombre") or "").strip():
        cargar_identidad_auxiliar(request)
    return not (request.session.get("auxiliar_nombre") or "").strip()


def _quien_reporta(request: HttpRequest) -> str:
    nombre = (request.session.get("auxiliar_nombre") or "").strip()
    if nombre or _es_auxiliar(request):
        return nombre
    usuario = request.session.get("usuario") or {}
    return str(usuario.get("display_name", "")).strip()


NOV_TABS = ("novedades", "objetos", "cierres")
NOV_TIPO = {"novedades": "novedad", "objetos": "objeto", "cierres": "cierre"}
NOV_VIGENCIA_DIAS = 3


def _detalle_res(res: object) -> object:
    try:
        data = res.json()  # type: ignore[union-attr]
    except ValueError:
        return res.text[:200]  # type: ignore[union-attr]
    return data.get("detail", data) if isinstance(data, dict) else data


@con_login
def novedades_vista(request: HttpRequest) -> HttpResponse:
    sin_vinculo = _sin_vinculo(request)
    tab = (request.POST.get("tab") or request.GET.get("tab") or "novedades").strip()
    if tab not in NOV_TABS:
        tab = "novedades"
    f_turno = (request.GET.get("f_turno") or "").strip()
    if f_turno not in TURNOS:
        f_turno = ""
    f_lab = (request.GET.get("f_lab") or "").strip()
    if not f_lab.isdigit():
        f_lab = ""
    token = str(request.session["jwt"])
    error = AVISO_SIN_VINCULO if sin_vinculo else ""
    puede_validar = _puede_reportes(request) or bool(
        request.session.get("auxiliar_encargado")
    )
    if request.method == "POST" and not (
        sin_vinculo
        and request.POST.get("action") in ("crear", "devolver", "validar", "rechazar")
    ):
        action = request.POST.get("action", "")
        try:
            if action == "crear":
                nombre = _quien_reporta(request)
                if not nombre:
                    raise ApiError(403, AVISO_SIN_VINCULO)
                data = {
                    "tipo": NOV_TIPO[tab],
                    "texto": (request.POST.get("texto") or "").strip(),
                    "auxiliar_nombre": nombre,
                    "turno": (request.POST.get("turno") or "").strip(),
                    "laboratorio_id": (request.POST.get("laboratorio_id") or "").strip(),
                }
                data = {k: v for k, v in data.items() if v != ""}
                files = None
                f = request.FILES.get("foto")
                if f is not None and (f.name or "").strip():
                    files = {"foto": (f.name, f.read(), f.content_type)}
                res = requests.post(
                    settings.FASTAPI_URL + "/api/novedades",
                    headers={"Authorization": f"Bearer {token}"},
                    data=data,
                    files=files,
                    timeout=TIMEOUT,
                )
                if res.status_code in (401, 403):
                    return redirect("login")
                if res.status_code >= 400:
                    raise ApiError(res.status_code, _detalle_res(res))
            elif action in ("devolver", "validar", "rechazar"):
                cuerpo_accion: dict[str, object] = {
                    "accion": action,
                    "auxiliar_nombre": _quien_reporta(request),
                }
                if action == "devolver":
                    cuerpo_accion["entregado_a"] = (
                        request.POST.get("entregado_a") or ""
                    ).strip()
                api_patch(
                    f"/api/novedades/{int(request.POST.get('id', '0'))}",
                    token,
                    cuerpo_accion,
                )
            elif action == "purgar":
                api_post("/api/novedades/purga", token, {})
        except ApiError as e:
            error = str(e.detail) if e.detail else "No se pudo procesar"
        except (ValueError, requests.RequestException):
            error = "No se pudo procesar"
        else:
            destino = f"{reverse('novedades')}?tab={tab}"
            if tab == "novedades" and f_turno:
                destino += f"&f_turno={quote(f_turno)}"
            if tab == "novedades" and f_lab:
                destino += f"&f_lab={quote(f_lab)}"
            return redirect(destino)
    filas: list[dict[str, object]] = []
    try:
        params: dict[str, str] = {"tipo": NOV_TIPO[tab]}
        if tab == "novedades":
            params["dias"] = str(NOV_VIGENCIA_DIAS)
            if f_turno:
                params["turno"] = f_turno
        datos = api_get("/api/novedades", token, params)
    except ApiError as e:
        error = str(e.detail) if e.detail else "No se pudo cargar"
    else:
        if isinstance(datos, list):
            filas = [d for d in datos if isinstance(d, dict)]
    if tab == "novedades" and f_lab and any("laboratorio_id" in d for d in filas):
        filas = [d for d in filas if str(d.get("laboratorio_id") or "") == f_lab]
    grupos: dict[str, list[dict[str, object]]] = {}
    if tab == "objetos":
        grupos = {"pendiente": [], "devuelto": [], "vencido": []}
        for fila in filas:
            grupos.setdefault(str(fila.get("estado", "pendiente")), []).append(fila)
    cards = _cards(token)
    return render(
        request,
        "atenciones/novedades.html",
        {
            "tab": tab,
            "filas": filas,
            "grupos": grupos,
            "labs": cards["activas"],
            "turnos": TURNOS,
            "puede_validar": puede_validar,
            "quien": _quien_reporta(request),
            "f_turno": f_turno,
            "f_lab": f_lab,
            "vigencia_dias": NOV_VIGENCIA_DIAS,
            "error": error,
            "flash": request.session.pop("flash", None),
        },
    )


@con_login
def novedad_foto_vista(request: HttpRequest, novedad_id: int) -> HttpResponse:
    token = str(request.session["jwt"])
    try:
        res = requests.get(
            f"{settings.FASTAPI_URL}/api/novedades/{novedad_id}/foto",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return HttpResponse(status=404)
    if res.status_code in (401, 403):
        return redirect("login")
    if res.status_code >= 400:
        return HttpResponse(status=404)
    return HttpResponse(res.content, content_type=res.headers.get("Content-Type", "image/jpeg"))


@con_login
def lab_nueva_vista(request: HttpRequest) -> HttpResponse:
    sin_vinculo = _sin_vinculo(request)
    aux_fijo = _es_auxiliar(request)
    token = str(request.session["jwt"])
    error = AVISO_SIN_VINCULO if sin_vinculo else ""
    post = request.POST
    if aux_fijo and request.method == "POST":
        # El auxiliar principal sale de la cuenta; los extras siguen libres.
        post = request.POST.copy()
        post["auxiliar_nombre"] = _quien_reporta(request)
    batch: list[dict[str, object]] = request.session.get("lab_batch", [])
    edit_idx = request.session.get("lab_edit_idx")
    if edit_idx is not None and not (0 <= edit_idx < len(batch)):
        edit_idx = None
        request.session.pop("lab_edit_idx", None)
    if request.method == "POST" and not sin_vinculo:
        action = request.POST.get("action")
        if action == "agregar":
            items, error = _items_lab_desde_post(post)
            if not error and items:
                if edit_idx is not None:
                    batch[edit_idx : edit_idx + 1] = items
                    request.session.pop("lab_edit_idx", None)
                    edit_idx = None
                else:
                    batch.extend(items)
                request.session["lab_batch"] = batch
                return redirect("lab_nueva")
            if edit_idx is not None and not error:
                request.session["lab_batch"] = batch
                return redirect("lab_nueva")
        elif action == "clonar":
            try:
                idx = int(request.POST.get("idx", "-1"))
                origen = batch[idx]
            except (IndexError, ValueError):
                error = "Índice inválido."
            else:
                pedidos: list[int] = []
                for k, v in request.POST.items():
                    if not k.startswith("copias_"):
                        continue
                    try:
                        lab_id = int(k.split("_", 1)[1])
                        n = int(str(v or "0"))
                    except (IndexError, ValueError):
                        continue
                    pedidos.extend([lab_id] * min(max(n, 0), 99))
                if not pedidos:
                    error = "Poné cuántas copias querés en al menos un laboratorio."
                else:
                    batch[idx + 1 : idx + 1] = [
                        {**origen, "laboratorio_id": lab_id, "_forzar": True}
                        for lab_id in pedidos
                    ]
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
                directos, error = _items_lab_desde_post(post)
                if directos:
                    a_enviar = directos
            if not a_enviar:
                if not error:
                    error = "Lista vacía."
            else:
                for item in a_enviar:
                    payload = {
                        k: v for k, v in item.items() if not str(k).startswith("_")
                    }
                    if item.get("_forzar"):
                        payload["forzar_duplicado"] = True
                    try:
                        api_post("/api/laboratorios/atenciones", token, payload)
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
    if aux_fijo:
        aux1 = _quien_reporta(request)
    # Prefill desde sala: ?lab=<id>&pc=<nombre> (solo lectura GET, no toca POST).
    lab_prefill = None
    _lab_raw = (request.GET.get("lab") or "").strip()
    if _lab_raw.isdigit():
        _lab_id = int(_lab_raw)
        if any(c.get("id") == _lab_id for c in cards["activas"]):
            lab_prefill = _lab_id
    pc_prefill = str(request.GET.get("pc") or "").strip()[:50]
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
            "aux_fijo": aux_fijo,
            "aux_extras": aux_extras,
            "edit_idx": edit_idx,
            "turnos": TURNOS,
            "medios": MEDIOS,
            "sugerencias_json": json.dumps(_sugerencias_por_turno(token)),
            "lab_prefill": lab_prefill,
            "pc_prefill": pc_prefill,
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
def lab_clonar_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    token = str(request.session["jwt"])
    error = ""
    try:
        origen = api_get(f"/api/laboratorios/atenciones/{atencion_id}", token)
    except ApiError as e:
        if e.status in (401, 403):
            return redirect("login")
        _flash(request, "error", "Atención no encontrada")
        return redirect("lab_lista")
    if not isinstance(origen, dict):
        return redirect("lab_lista")
    puede = (
        origen.get("usuario_id") == (request.session.get("usuario") or {}).get("id")
        or _puede_reportes(request)
        or _es_encargado(request)
    )
    if not puede:
        _flash(request, "error", "Solo el dueño o un encargado puede clonar")
        return redirect("lab_lista")
    cards = _cards(token)
    if request.method == "POST":
        labs_a_clonar: list[int] = []
        for lab in cards["activas"]:
            try:
                cantidad = int(str(request.POST.get(f"copias_{lab['id']}", "0")))
            except (TypeError, ValueError):
                cantidad = 0
            if cantidad:
                labs_a_clonar.extend(
                    [int(lab["id"])] * min(max(cantidad, 0), 99)
                )
        if not labs_a_clonar:
            error = "Poné cuántas copias querés en al menos un laboratorio."
        else:
            def tomar(campo: str, default: object) -> str:
                valor = str(request.POST.get(campo) or "").strip()
                return valor if valor else str(default or "")

            base = {
                "categoria": tomar("categoria", origen.get("categoria", "")),
                "auxiliar_nombre": tomar(
                    "auxiliar_nombre", origen.get("auxiliar_nombre", "")
                ),
                "descripcion": tomar("descripcion", origen.get("descripcion", "")),
                "solucion": tomar("solucion", origen.get("solucion", "")),
                "medio_solicitud": tomar(
                    "medio_solicitud", origen.get("medio_solicitud") or "Presencial"
                ),
                "fecha_registro": tomar(
                    "fecha_registro", origen.get("fecha_registro") or _hoy_iso()
                ),
            }
            turno = str(request.POST.get("turno") or "").strip()
            if not turno:
                turno = str(origen.get("turno") or "")
            if turno in TURNOS:
                base["turno"] = turno
            obs = str(request.POST.get("observaciones") or "").strip()
            if not obs:
                obs = str(origen.get("observaciones") or "")
            if obs:
                base["observaciones"] = obs
            creadas = 0
            for lab_id in labs_a_clonar:
                copia = {
                    **base,
                    "laboratorio_id": lab_id,
                    "forzar_duplicado": True,
                }
                try:
                    api_post("/api/laboratorios/atenciones", token, copia)
                except ApiError as e:
                    if creadas:
                        _flash(
                            request,
                            "ok",
                            f"{creadas} copia(s) creada(s); la siguiente falló: "
                            + str(e.detail),
                        )
                    else:
                        _flash(
                            request,
                            "error",
                            str(e.detail) if e.detail else "No se pudo clonar",
                        )
                    return redirect("lab_lista")
                creadas += 1
            _flash(request, "ok", f"{creadas} copia(s) creada(s). Editá cada una para diferenciarla.")
            return redirect("lab_lista")
    return render(
        request,
        "atenciones/laboratorios_clonar.html",
        {
            "origen": origen,
            "activas": cards["activas"],
            "categorias": _categorias(token),
            "turnos": TURNOS,
            "medios": MEDIOS,
            "error": error,
        },
    )


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
def lab_tablero_vista(request: HttpRequest) -> HttpResponse:
    # ponytail: solo lectura, agrega 3 llamadas API y deriva el semáforo en Django.
    if not (_puede_reportes(request) or _es_encargado(request)):
        return redirect("lab_lista")
    token = str(request.session["jwt"])
    try:
        cards = api_get("/api/laboratorios/cards", token)
        atenciones = api_get("/api/laboratorios/atenciones", token)
        objetos = api_get(
            "/api/novedades", token, {"tipo": "objeto", "estado": "pendiente"}
        )
    except ApiError as e:
        if e.status in (401, 403):
            raise
        _log.error("LAB-TABLERO fallo: %s", e.detail)
        return render(
            request, "atenciones/tablero.html", {"error": True}, status=502
        )
    labs = []
    if isinstance(cards, dict):
        labs = [
            lab
            for lab in (cards.get("activas") or [])
            if isinstance(lab, dict)
        ]
    filas = (
        [a for a in atenciones if isinstance(a, dict)]
        if isinstance(atenciones, list)
        else []
    )
    pendientes = (
        [o for o in objetos if isinstance(o, dict)]
        if isinstance(objetos, list)
        else []
    )
    corte = (_dt.datetime.now(_dt.UTC).date() - _dt.timedelta(days=7)).isoformat()
    tarjetas = []
    for lab in labs:
        lid = lab.get("id")
        recientes = [
            a
            for a in filas
            if a.get("laboratorio_id") == lid
            and str(a.get("fecha_registro", "")) >= corte
        ]
        vistos: dict[str, str] = {}
        for a in recientes:
            crudo = str(a.get("pc_nombre") or "").strip()
            if crudo and crudo.upper() not in vistos:
                vistos[crudo.upper()] = crudo
        pcs_falla = sorted(vistos.values(), key=str.upper)
        objs = [o for o in pendientes if o.get("laboratorio_id") == lid]
        ultimas = sorted(
            (a for a in filas if a.get("laboratorio_id") == lid),
            key=lambda a: (str(a.get("fecha_registro", "")), int(a.get("id", 0) or 0)),
            reverse=True,
        )
        ultima = ultimas[0] if ultimas else None
        total_pcs = None
        with contextlib.suppress(ApiError):
            pcs = api_get(f"/api/laboratorios/{lid}/pcs", token)
            if isinstance(pcs, dict):
                total_pcs = len(pcs.get("pcs", []))
        semaforo = "verde"
        if objs:
            semaforo = "rojo"
        elif pcs_falla:
            semaforo = "amarillo"
        tarjetas.append(
            {
                "codigo": lab.get("codigo", ""),
                "nombre": lab.get("nombre", ""),
                "lab_id": lid,
                "semaforo": semaforo,
                "atenciones_7d": len(recientes),
                "pcs_falla": pcs_falla,
                "total_pcs": total_pcs,
                "objetos": len(objs),
                "ultima": (
                    {
                        "fecha": str(ultima.get("fecha_registro", "")),
                        "auxiliar": str(ultima.get("auxiliar_nombre", "")),
                        "categoria": str(ultima.get("categoria", "")),
                    }
                    if isinstance(ultima, dict)
                    else None
                ),
            }
        )
    resumen = {
        "rojos": sum(1 for t in tarjetas if t["semaforo"] == "rojo"),
        "amarillos": sum(1 for t in tarjetas if t["semaforo"] == "amarillo"),
        "verdes": sum(1 for t in tarjetas if t["semaforo"] == "verde"),
    }
    return render(
        request,
        "atenciones/tablero.html",
        {"error": False, "tarjetas": tarjetas, "resumen": resumen},
    )


@con_login
def lab_timeline_vista(request: HttpRequest) -> HttpResponse:
    # ponytail: solo lectura, 2 llamadas API y orden cronológico en Django.
    token = str(request.session["jwt"])
    hoy = _dt.datetime.now(_dt.UTC).date().isoformat()
    try:
        atenciones = api_get("/api/laboratorios/atenciones", token)
        novedades = api_get("/api/novedades", token, {"dias": "1"})
    except ApiError as e:
        if e.status in (401, 403):
            raise
        _log.error("LAB-TIMELINE fallo: %s", e.detail)
        return render(
            request, "atenciones/timeline.html", {"error": True}, status=502
        )
    eventos = []
    for a in atenciones if isinstance(atenciones, list) else []:
        if not isinstance(a, dict) or str(a.get("fecha_registro", "")) != hoy:
            continue
        eventos.append(
            {
                "hora": str(a.get("created_at", ""))[11:16],
                "icono": "🧰",
                "titulo": f"{a.get('laboratorio', '')} · {a.get('categoria', '')}",
                "detalle": str(a.get("descripcion", "")),
                "auxiliar": str(a.get("auxiliar_nombre", "")),
                "foto_id": None,
                "orden": str(a.get("created_at", "")),
            }
        )
    for n in novedades if isinstance(novedades, list) else []:
        if not isinstance(n, dict) or str(n.get("fecha_registro", "")) != hoy:
            continue
        tipo = str(n.get("tipo", ""))
        estado = str(n.get("estado", ""))
        if tipo == "objeto":
            icono = "🎒✅" if estado == "devuelto" else "🎒"
            titulo = f"Objeto {estado}: {n.get('texto', '')}"
            if estado == "devuelto" and n.get("entregado_a"):
                titulo += f" → {n.get('entregado_a')}"
        elif tipo == "cierre":
            icono = "🔑✅" if estado == "validado" else "🔑"
            titulo = f"Cierre {estado}: {n.get('texto', '')}"
        else:
            icono = "📢"
            titulo = str(n.get("texto", ""))
        eventos.append(
            {
                "hora": str(n.get("created_at", ""))[11:16],
                "icono": icono,
                "titulo": titulo,
                "detalle": str(n.get("laboratorio", "") or n.get("turno", "")),
                "auxiliar": str(n.get("auxiliar_nombre", "")),
                "foto_id": n.get("id") if n.get("tiene_foto") else None,
                "orden": str(n.get("created_at", "")),
            }
        )
    eventos.sort(key=lambda e: str(e["orden"]), reverse=True)
    return render(
        request,
        "atenciones/timeline.html",
        {"error": False, "eventos": eventos, "hoy": hoy},
    )


@con_login
def horarios_export_xlsx_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    es_pdf = request.path.endswith(".pdf")
    params = {
        k: v for k in ("tipo", "mes", "anio") if (v := request.GET.get(k))
    } or {"tipo": "sabado"}
    res = requests.get(
        settings.FASTAPI_URL + "/api/laboratorios/horarios/export." + ("pdf" if es_pdf else "xlsx"),
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=TIMEOUT,
    )
    if res.status_code in (401, 403):
        return redirect("login")
    destino = "auxiliares_horarios" if params.get("tipo") == "semanal" else "auxiliares_sabados"
    if res.status_code >= 400:
        _flash(request, "error", "No se pudo exportar el archivo")
        return redirect(destino)
    nombre = "horarios." + ("pdf" if es_pdf else "xlsx")
    disp = res.headers.get("Content-Disposition", "")
    if "filename=" in disp:
        nombre = disp.split("filename=", 1)[1].strip().strip('"')
    resp = HttpResponse(
        res.content,
        content_type="application/pdf"
        if es_pdf
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f"attachment; filename={nombre}"
    return resp


FICHA_CAMPOS = (
    "procesador",
    "ram",
    "disco",
    "marca",
    "gpu",
    "monitores",
    "sillas",
    "capacidad",
    "pcs_estudiantes",
    "pcs_docentes",
)


@con_login
def lab_pcs_vista(request: HttpRequest, laboratorio_id: int) -> HttpResponse:
    token = str(request.session["jwt"])
    error = ""

    # estados de una PC bajo demanda: GET /pcs/<id>/?estados=<pc_id>
    pc_estados = request.GET.get("estados")
    if pc_estados:
        try:
            filas_estados = api_get(f"/api/software/pcs/{int(pc_estados)}", token)
        except (ApiError, ValueError) as e:
            detalle = str(getattr(e, "detail", "")) or "PC inválida"
            return JsonResponse({"ok": False, "error": detalle}, status=400)
        return JsonResponse({"ok": True, "estados": filas_estados})

    nombre_lab = ""
    ficha: dict[str, object] = {}
    pcs: dict[str, object] = {"filas": 0, "cols": 0, "pcs": []}
    cards = _cards(token)
    for c in cards["activas"] + cards["inactivas"]:
        if c.get("id") == laboratorio_id:
            nombre_lab = str(c.get("codigo", ""))
            ficha = {
                campo: c.get(campo)
                for campo in FICHA_CAMPOS
                if c.get(campo) not in (None, "")
            }
            break

    if request.method == "POST":
        try:
            cuerpo = json.loads(request.body or b"{}")
        except ValueError:
            cuerpo = None
        if not isinstance(cuerpo, dict):
            return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)
        accion = str(cuerpo.pop("accion", "dibujo"))
        try:
            if accion == "marcar":
                if _sin_vinculo(request):
                    return JsonResponse(
                        {"ok": False, "error": AVISO_SIN_VINCULO}, status=403
                    )
                pc_id = int(cuerpo.pop("pc_id", 0))
                cuerpo.setdefault("auxiliar_nombre", _quien_reporta(request))
                api_put(f"/api/software/pcs/{pc_id}", token, cuerpo)
            elif accion == "ficha":
                # se envían todos los campos; vacío = limpiar (el API acepta null)
                cuerpo = {k: v for k, v in cuerpo.items() if k in FICHA_CAMPOS}
                api_put(f"/api/laboratorios/{laboratorio_id}", token, cuerpo)
            else:
                api_put(f"/api/laboratorios/{laboratorio_id}/pcs", token, cuerpo)
        except ApiError as e:
            detalle = str(e.detail) if e.detail else "No se pudo guardar"
            return JsonResponse({"ok": False, "error": detalle}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)
        return JsonResponse({"ok": True})

    try:
        datos = api_get(f"/api/laboratorios/{laboratorio_id}/pcs", token)
    except ApiError as e:
        if e.status in (401, 403):
            return redirect("login")
        _flash(request, "error", str(e.detail) if e.detail else "No se pudo cargar")
        return redirect("lab_lista")
    if isinstance(datos, dict):
        pcs = datos
    # software del lab: lectura tolerante (si falla, la sala se ve igual)
    sw_lab: list[dict[str, object]] = []
    try:
        sw_lab = [
            s
            for s in (api_get(f"/api/software/laboratorios/{laboratorio_id}", token) or [])
            if isinstance(s, dict)
        ]
    except ApiError:
        sw_lab = []
    prefijo = None
    base = None
    import re as _re

    m = _re.search(r"(\d+)", nombre_lab)
    if m and nombre_lab.upper().startswith("LAB"):
        n = int(m.group(1))
        prefijo, base = "SCPC ", n * 100
    pcs_json = json.dumps(
        {
            "filas": int(pcs.get("filas") or 0),
            "cols": int(pcs.get("cols") or 0),
            "pcs": [
                {
                    "id": int(p.get("id") or 0),
                    "nombre": str(p.get("nombre", "")),
                    "fila": int(p.get("fila") or 0),
                    "col": int(p.get("col") or 0),
                    "activa": bool(p.get("activa", True)),
                }
                for p in (pcs.get("pcs") or [])
                if isinstance(p, dict)
            ],
        }
    )
    meta_json = json.dumps({"prefijo": prefijo, "base": base})
    return render(
        request,
        "atenciones/laboratorios_pcs.html",
        {
            "lab_id": laboratorio_id,
            "lab_codigo": nombre_lab or f"Lab #{laboratorio_id}",
            "pcs_json": pcs_json,
            "meta_json": meta_json,
            "ficha_json": json.dumps(ficha),
            "sw_lab_json": json.dumps(sw_lab),
            "puede_ficha": _rol(request) in ("Jefe", "Encargado"),
            "quien": _quien_reporta(request),
            "error": error,
        },
    )


def _sw_desde_post(post: object) -> dict[str, object]:
    def get(campo: str) -> str:
        return str(post.get(campo, "") or "").strip()  # type: ignore[union-attr]

    def marca(campo: str) -> bool:
        return post.get(campo) in ("on", "1", "true", "True")  # type: ignore[union-attr]

    return {
        "nombre": get("nombre"),
        "licencia": get("licencia") or "gratuita",
        "uso": get("uso"),
        "esencial": marca("esencial"),
        "docentes": marca("docentes"),
        "activo": marca("activo"),
    }


def _plantilla_desde_post(post: object) -> dict[str, object]:
    def get(campo: str) -> str:
        return str(post.get(campo, "") or "").strip()  # type: ignore[union-attr]

    return {
        "nombre": get("nombre"),
        "categoria": get("categoria") or "SOFTWARE",
        "descripcion": get("descripcion"),
        "solucion": get("solucion"),
        "turno": get("turno") or None,
        "activa": post.get("activa") in ("on", "1", "true", "True"),  # type: ignore[union-attr]
    }


@con_login
def software_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    error = ""
    lab_sel = request.GET.get("lab", "").strip()
    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if action == "crear":
                api_post("/api/software", token, _sw_desde_post(request.POST))
            elif action == "editar":
                api_put(
                    f"/api/software/{int(request.POST.get('id', 0))}",
                    token,
                    _sw_desde_post(request.POST),
                )
            elif action == "plantilla":
                pid = int(request.POST.get("id", 0) or 0)
                cuerpo = _plantilla_desde_post(request.POST)
                if pid:
                    api_put(f"/api/software/plantillas/{pid}", token, cuerpo)
                else:
                    api_post("/api/software/plantillas", token, cuerpo)
            elif action == "matriz":
                lab_id = int(request.POST.get("lab_id", 0))
                ids = [
                    int(v)
                    for v in request.POST.getlist("software_ids")
                    if str(v).strip()
                ]
                api_put(f"/api/software/laboratorios/{lab_id}", token, {"software_ids": ids})
                lab_sel = str(lab_id)
            else:
                error = "Acción desconocida."
        except ApiError as e:
            error = str(e.detail) if e.detail else "No se pudo guardar"
        except (TypeError, ValueError):
            error = "Datos inválidos."
        else:
            if not error:
                destino = reverse("software") + (f"?lab={lab_sel}" if lab_sel else "")
                return redirect(destino)
    sws: list[dict[str, object]] = []
    plantillas: list[dict[str, object]] = []
    try:
        sws = [s for s in (api_get("/api/software", token) or []) if isinstance(s, dict)]
    except ApiError as e:
        error = str(e.detail) if e.detail else "No se pudo cargar"
    try:
        plantillas = [
            p
            for p in (api_get("/api/software/plantillas", token) or [])
            if isinstance(p, dict)
        ]
    except ApiError:
        plantillas = []
    cards = _cards(token)
    sw_lab_ids: list[int] = []
    if lab_sel:
        try:
            sw_lab_ids = [
                int(s.get("id") or 0)
                for s in (api_get(f"/api/software/laboratorios/{int(lab_sel)}", token) or [])
                if isinstance(s, dict)
            ]
        except (ApiError, ValueError):
            sw_lab_ids = []
    return render(
        request,
        "atenciones/software.html",
        {
            "sws": sws,
            "plantillas": plantillas,
            "sws_json": json.dumps(sws),
            "plantillas_json": json.dumps(plantillas),
            "labs": cards["activas"],
            "lab_sel": lab_sel,
            "sw_lab_ids": sw_lab_ids,
            "categorias": _categorias(token),
            "turnos": TURNOS,
            "puede_editar": _rol(request) in ("Jefe", "Encargado"),
            "quien": _quien_reporta(request),
            "error": error,
            "flash": request.session.pop("flash", None),
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


@con_login
def auditoria_vista(request: HttpRequest) -> HttpResponse:
    """Rastro de cambios esenciales. Solo Jefes (o con dashboard); ni Encargado ni Auxiliar."""
    if not _puede_reportes(request):
        return redirect("lab_lista")
    token = str(request.session["jwt"])
    error = ""
    params: dict[str, str] = {"limite": request.GET.get("limite", "200")}
    for campo in ("entidad", "accion"):
        valor = (request.GET.get(campo) or "").strip()
        if valor:
            params[campo] = valor
    filas: list[dict[str, object]] = []
    try:
        datos = api_get("/api/auditoria", token, params)
    except ApiError as e:
        if e.status in (401, 403):
            return redirect("lab_lista")
        error = str(e.detail) if e.detail else "No se pudo cargar"
    else:
        if isinstance(datos, list):
            filas = [f for f in datos if isinstance(f, dict)]
    return render(
        request,
        "atenciones/auditoria.html",
        {
            "filas": filas,
            "total": len(filas),
            "entidad_sel": params.get("entidad", ""),
            "accion_sel": params.get("accion", ""),
            "entidades": (
                "laboratorio",
                "software",
                "software_lab",
                "pcs_lab",
                "atencion",
                "atencion_lab",
                "categoria",
            ),
            "acciones": ("crear", "editar", "eliminar"),
            "error": error,
            "flash": request.session.pop("flash", None),
        },
    )
