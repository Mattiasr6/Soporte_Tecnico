import calendar
import contextlib
import datetime as _dt
import json as _json
import logging
from zoneinfo import ZoneInfo

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .api import (
    ApiError,
    api_delete,
    api_get,
    api_patch,
    api_post,
    api_put,
    login_api,
)
from .auth import con_login
from .forms import LoginForm

_ZONA_LA_PAZ = ZoneInfo("America/La_Paz")

_log = logging.getLogger(__name__)

PASO_LISTA = 50

CATEGORIAS = [
    "Audio/Video",
    "Cuentas/Accesos",
    "Hardware",
    "Impresión",
    "Otros",
    "Redes/Conectividad",
    "Sistemas académicos",
    "Software",
]
MEDIOS = ["Interno", "Presencial", "WhatsApp", "E-ticket"]
SOLICITANTES = ["ADM", "BEC", "DOC", "EST"]
TOP_HEATMAP = 6
TOP_PARETO = 8


def _rol(request: HttpRequest) -> str:
    usuario = request.session.get("usuario") or {}
    return str(usuario.get("role", ""))


def _es_auxiliar(request: HttpRequest) -> bool:
    return _rol(request) == "Auxiliar"


def _puede_dashboard(request: HttpRequest) -> bool:
    usuario = request.session.get("usuario") or {}
    return _rol(request) == "Jefe" or bool(usuario.get("can_view_dashboard"))


def login_vista(request: HttpRequest) -> HttpResponse:
    if request.session.get("jwt") and request.method == "GET":
        return redirect(_destino(request))
    error = ""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                data = login_api(
                    form.cleaned_data["email"], form.cleaned_data["password"]
                )
                request.session["jwt"] = data["token"]
                request.session["usuario"] = data["user"]
                _marcar_sesion(request, True)
                return redirect(_destino(request))
            except ApiError as e:
                error = str(e.detail) if e.detail else "No se pudo entrar"
    else:
        form = LoginForm()
    return render(request, "atenciones/login.html", {"form": form, "error": error})


def _destino(request: HttpRequest) -> str:
    return "auxiliares" if _es_auxiliar(request) else "inicio"


@con_login
def inicio_vista(request: HttpRequest) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    _marcar_sesion(request, True)
    token = str(request.session["jwt"])
    usuarios = api_get("/api/usuarios", token)
    assert isinstance(usuarios, list)
    conteo, tecnicos = _presencia(usuarios)
    yo = api_get("/api/usuarios/me", token)
    datos_yo = yo if isinstance(yo, dict) else {}
    anuncio = api_get("/api/announcements", token)
    return render(
        request,
        "atenciones/inicio.html",
        {
            "conteo": conteo,
            "tecnicos": tecnicos,
            "yo": datos_yo,
            "yo_etiqueta": _etiqueta_estado(datos_yo.get("estado_actual", "")),
            "anuncio": anuncio if isinstance(anuncio, dict) else {},
        },
    )


@con_login
def inicio_anuncio_vista(request: HttpRequest) -> JsonResponse:
    anuncio = api_get("/api/announcements", str(request.session["jwt"]))
    return JsonResponse(anuncio if isinstance(anuncio, dict) else {})


@con_login
@require_POST
def inicio_anuncio_guardar_vista(request: HttpRequest) -> JsonResponse:
    if not _puede_dashboard(request):
        return JsonResponse(
            {"ok": False, "error": "Solo un jefe puede publicar el anuncio."}, status=403
        )
    try:
        anuncio = api_post(
            "/api/announcements",
            str(request.session["jwt"]),
            {"message": request.POST.get("mensaje", "")},
        )
    except ApiError as e:
        return JsonResponse({"ok": False, "error": _detalle_error(e)}, status=e.status)
    return JsonResponse({"ok": True, "anuncio": anuncio})


@con_login
@require_POST
def inicio_estado_vista(request: HttpRequest) -> JsonResponse:
    estado = request.POST.get("estado", "").strip().lower()
    try:
        api_patch(
            "/api/usuarios/estado",
            str(request.session["jwt"]),
            {"estado_actual": estado},
        )
    except ApiError as e:
        return JsonResponse({"ok": False, "error": _detalle_error(e)}, status=e.status)
    return JsonResponse({"ok": True, "estado": estado})


def logout_vista(request: HttpRequest) -> HttpResponse:
    _marcar_sesion(request, False)
    request.session.flush()
    return redirect("login")


def _tecnicos_para_filtrar(token: str) -> list[dict[str, object]]:
    usuarios = api_get("/api/usuarios", token, {"incluir_inactivos": "true"})
    if not isinstance(usuarios, list):
        return []
    tecnicos = [
        {
            "id": u["id"],
            "nombre": u["display_name"] + ("" if u.get("activo") else " (de baja)"),
        }
        for u in usuarios
        if isinstance(u, dict) and u.get("role") in ("Tecnico", "Jefe")
    ]
    return sorted(tecnicos, key=lambda t: str(t["nombre"]))


@con_login
def lista_vista(request: HttpRequest) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    token = request.session["jwt"]
    usuario = request.session["usuario"]
    q = request.GET.get("q", "").strip().lower()
    categoria = request.GET.get("categoria", "").strip()
    mes = request.GET.get("mes", "").strip()
    tecnico = _int_o_none(request.GET.get("tecnico"))
    params = {"usuario_id": str(tecnico)} if tecnico else None
    data = api_get("/api/atenciones", token, params)
    assert isinstance(data, list)
    filas = [a for a in data if isinstance(a, dict)]
    if q:
        filas = [
            a
            for a in filas
            if q in str(a.get("descripcion", "")).lower()
            or q in str(a.get("area_solicitante", "")).lower()
        ]
    if categoria:
        filas = [a for a in filas if a.get("categoria") == categoria]
    if mes:
        filas = [a for a in filas if str(a.get("fecha_registro", ""))[:7] == mes]
    limite = min(
        max(_int_o_none(request.GET.get("limite")) or PASO_LISTA, PASO_LISTA), 500
    )
    return render(
        request,
        "atenciones/lista.html",
        {
            "atenciones": filas[:limite],
            "total": len(filas),
            "limite": limite,
            "siguiente_limite": min(limite + PASO_LISTA, 500),
            "hay_mas": len(filas) > limite,
            "restantes": max(len(filas) - limite, 0),
            "usuario": usuario,
            "q": request.GET.get("q", ""),
            "categoria": categoria,
            "mes": mes,
            "tecnico": tecnico,
            "tecnicos": _tecnicos_para_filtrar(token) if _puede_dashboard(request) else [],
            "flash": request.session.pop("flash", None),
        },
    )


@con_login
def nueva_vista(request: HttpRequest) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    token = request.session["jwt"]
    error = ""
    batch = request.session.get("batch", [])
    edit_idx = request.session.get("edit_idx")
    if edit_idx is not None and not (0 <= edit_idx < len(batch)):
        edit_idx = None
        request.session.pop("edit_idx", None)
    edit_item = batch[edit_idx] if edit_idx is not None else None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "agregar":
            area_id = request.POST.get("area_id") or None
            descripcion = request.POST.get("descripcion", "").strip()
            solucion = request.POST.get("solucion", "").strip()
            categoria = request.POST.get("categoria", "").strip()
            if not area_id:
                error = "Elige un área."
            elif not descripcion or not solucion or not categoria:
                error = "Faltan descripción, solución o categoría."
            else:
                colab = request.POST.get("colaborador_id") or None
                item = {
                    "area_solicitante": "",
                    "grupo_padre_id": _int_o_none(request.POST.get("grupo_padre_id")),
                    "grupo_id": _int_o_none(request.POST.get("grupo_id")),
                    "area_id": int(area_id),
                    "medio_solicitud": request.POST.get("medio_solicitud", "Interno"),
                    "usuario_solicitante": request.POST.get(
                        "usuario_solicitante", "ADM"
                    ),
                    "categoria": categoria,
                    "descripcion": descripcion,
                    "solucion": solucion,
                    "observaciones": request.POST.get("observaciones") or None,
                    "enlace_apoyo": request.POST.get("enlace_apoyo") or None,
                    "colaborador_id": int(colab) if colab else None,
                    "fecha_registro": request.POST.get("fecha_registro") or _hoy_iso(),
                }
                if edit_idx is not None:
                    batch[edit_idx] = item
                    request.session.pop("edit_idx", None)
                    edit_idx = None
                    edit_item = None
                else:
                    batch.append(item)
                request.session["batch"] = batch
                return redirect("atenciones_nueva")
        elif action == "editar":
            try:
                idx = int(request.POST.get("idx", "-1"))
                _ = batch[idx]
            except (IndexError, ValueError):
                error = "Índice inválido."
            else:
                request.session["edit_idx"] = idx
                return redirect("atenciones_nueva")
        elif action == "cancelar_edicion":
            request.session.pop("edit_idx", None)
            return redirect("atenciones_nueva")
        elif action == "quitar":
            try:
                batch.pop(int(request.POST.get("idx", "-1")))
            except (IndexError, ValueError):
                error = "Índice inválido."
            request.session.pop("edit_idx", None)
            edit_idx = None
            edit_item = None
            request.session["batch"] = batch
            return redirect("atenciones_nueva")
        elif action == "enviar":
            if not batch:
                error = "Batch vacío."
            else:
                try:
                    api_post("/api/atenciones/batch", token, {"atenciones": batch})
                except ApiError as e:
                    error = str(e.detail) if e.detail else "No se pudo enviar"
                else:
                    request.session["batch"] = []
                    request.session.pop("edit_idx", None)
                    return redirect("atenciones_lista")
    arbol = api_get("/api/jerarquia/arbol", token)
    usuarios = api_get("/api/usuarios", token)
    recientes = api_get("/api/atenciones", token, {"limit": 10})
    try:
        stats = api_get("/api/atenciones/stats", token)
    except ApiError:
        stats = None
    assert isinstance(arbol, dict) and isinstance(usuarios, list)
    assert isinstance(recientes, list)
    conteos: dict[str, object] = {"padres": [], "grupos": [], "areas": []}
    if isinstance(stats, dict):
        conteos = {
            "padres": stats.get("por_padre") or [],
            "grupos": stats.get("por_grupo") or [],
            "areas": stats.get("por_area_id") or [],
        }
    return render(
        request,
        "atenciones/nueva.html",
        {
            "arbol_json": _json.dumps(arbol),
            "conteos_json": _json.dumps(conteos),
            "usuarios": [u for u in usuarios if isinstance(u, dict)],
            "recientes": [a for a in recientes if isinstance(a, dict)][:10],
            "batch": batch,
            "categorias": CATEGORIAS,
            "medios": MEDIOS,
            "solicitantes": SOLICITANTES,
            "error": error,
            "hoy": _hoy_iso(),
            "edit_item": edit_item,
            "edit_idx": edit_idx,
        },
    )


def _int_o_none(valor: object) -> int | None:
    try:
        return int(str(valor))
    except (TypeError, ValueError):
        return None


def _hoy_iso() -> str:
    return _dt.datetime.now(_dt.UTC).date().isoformat()


@con_login
def auxiliares_vista(request: HttpRequest) -> HttpResponse:
    if not (_es_auxiliar(request) or _puede_dashboard(request)):
        return redirect("atenciones_lista")
    return render(
        request, "atenciones/auxiliares.html", {"usuario": request.session["usuario"]}
    )


def _marcar_sesion(request: HttpRequest, conectado: bool) -> None:
    usuario = request.session.get("usuario")
    if not isinstance(usuario, dict) or usuario.get("role") == "Auxiliar":
        return
    token = request.session.get("jwt")
    if not token:
        return
    with contextlib.suppress(ApiError):
        api_post("/api/usuarios/sesion", str(token), {"conectado": conectado})


def _flash(request: HttpRequest, tipo: str, texto: str) -> None:
    request.session["flash"] = {"tipo": tipo, "texto": texto}


def _buscar(request: HttpRequest, atencion_id: int) -> dict[str, object]:
    data = api_get("/api/atenciones", request.session["jwt"])
    assert isinstance(data, list)
    for item in data:
        if isinstance(item, dict) and item.get("id") == atencion_id:
            return item
    raise Http404("Atención no encontrada")


@con_login
def ticket_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    token = request.session["jwt"]
    usuario = request.session["usuario"]
    atencion = _buscar(request, atencion_id)
    es_dueno = atencion.get("usuario_id") == usuario.get("id")
    ctx: dict[str, object] = {
        "a": atencion,
        "puede_editar": es_dueno,
        "puede_eliminar": es_dueno,
        "categorias": CATEGORIAS,
        "medios": MEDIOS,
        "solicitantes": SOLICITANTES,
        "edit_item": atencion,
        "hoy": _hoy_iso(),
    }
    if ctx["puede_editar"]:
        ctx["arbol_json"] = _json.dumps(api_get("/api/jerarquia/arbol", token))
        ctx["usuarios"] = api_get("/api/usuarios", token)
    return render(request, "atenciones/_ticket.html", ctx)


def _cuerpo_edicion(request: HttpRequest) -> dict[str, object]:
    cuerpo: dict[str, object] = {
        "medio_solicitud": request.POST.get("medio_solicitud", ""),
        "usuario_solicitante": request.POST.get("usuario_solicitante", ""),
        "categoria": request.POST.get("categoria", ""),
        "descripcion": request.POST.get("descripcion", ""),
        "solucion": request.POST.get("solucion", ""),
        "observaciones": request.POST.get("observaciones", ""),
        "enlace_apoyo": request.POST.get("enlace_apoyo", ""),
        "fecha_registro": request.POST.get("fecha_registro", ""),
    }
    for campo in ("grupo_padre_id", "grupo_id", "area_id", "colaborador_id"):
        valor = _int_o_none(request.POST.get(campo))
        if valor is not None:
            cuerpo[campo] = valor
    return {k: v for k, v in cuerpo.items() if v != ""}


@con_login
def atencion_editar_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    if request.method != "POST":
        return redirect("atenciones_lista")
    try:
        api_put(
            f"/api/atenciones/{atencion_id}",
            request.session["jwt"],
            _cuerpo_edicion(request),
        )
    except ApiError as e:
        _flash(request, "error", str(e.detail) if e.detail else "No se pudo guardar")
    else:
        _flash(request, "ok", f"Atención #{atencion_id} actualizada")
    return redirect("atenciones_lista")


@con_login
def atencion_eliminar_vista(request: HttpRequest, atencion_id: int) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    if request.method != "POST":
        return redirect("atenciones_lista")
    try:
        api_delete(f"/api/atenciones/{atencion_id}", request.session["jwt"])
    except ApiError as e:
        _flash(request, "error", str(e.detail) if e.detail else "No se pudo eliminar")
    else:
        _flash(request, "ok", f"Atención #{atencion_id} eliminada")
    return redirect("atenciones_lista")


def _params_stats(request: HttpRequest) -> dict[str, str]:
    params: dict[str, str] = {}
    for clave in ("grupo_padre_id", "grupo_id", "area_id"):
        valor = request.GET.get(clave, "").strip()
        if valor:
            params[clave] = valor
    for prefijo in ("desde", "hasta"):
        valor = request.GET.get(prefijo, "").strip()
        if len(valor) == 7 and valor[4] == "-":
            anio, mes = valor.split("-")
            params[f"{prefijo}_anio"] = anio
            params[f"{prefijo}_mes"] = mes
    return params


ORDEN_PRESENCIA = ("disponible", "ocupado", "extraturno", "ausente")
_PRIORIDAD_PRESENCIA = {estado: i for i, estado in enumerate(ORDEN_PRESENCIA)}
ETIQUETAS_ESTADO = {
    "disponible": "Disponible",
    "ocupado": "Ocupado",
    "extraturno": "Fuera de turno",
    "ausente": "Ausente",
}


def _etiqueta_estado(estado: object) -> str:
    return ETIQUETAS_ESTADO.get(str(estado), str(estado))


def _presencia(
    usuarios: list[object],
) -> tuple[dict[str, int], list[dict[str, object]]]:
    conteo: dict[str, int] = dict.fromkeys(ORDEN_PRESENCIA, 0)
    tecnicos: list[dict[str, object]] = []
    for u in usuarios:
        if not isinstance(u, dict):
            continue
        estado = str(u.get("estado_actual", "ausente"))
        if estado in conteo:
            conteo[estado] += 1
        tecnicos.append(
            {
                "nombre": u.get("display_name", ""),
                "rol": u.get("role", ""),
                "estado": estado,
                "etiqueta": _etiqueta_estado(estado),
                "horario_hoy": u.get("horario_hoy"),
                "entra_a_las": u.get("entra_a_las"),
                "atenciones_hoy": int(u.get("atenciones_hoy") or 0),
            }
        )
    tecnicos.sort(
        key=lambda t: (
            _PRIORIDAD_PRESENCIA.get(str(t["estado"]), 9),
            str(t["nombre"]),
        )
    )
    return conteo, tecnicos


def _mes_etiqueta(anio: int, mes: int) -> str:
    return f"{anio}-{mes:02d}"


MESES_CORTOS = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def _mes_corto(anio: int, mes: int) -> str:
    return f"{MESES_CORTOS[mes - 1]} {anio}"


def _graficos(stats: dict[str, object]) -> dict[str, object]:
    por_categoria = list(stats.get("por_categoria") or [])
    por_categoria.sort(key=lambda c: -int(c["total"]))  # type: ignore[index]
    total = int(stats.get("total") or 0)

    acumulado: list[float] = []
    corrido = 0
    for c in por_categoria:
        corrido += int(c["total"])  # type: ignore[index]
        acumulado.append(round(corrido * 100 / total, 1) if total else 0.0)

    cat_mes = list(stats.get("por_categoria_mes") or [])
    top_cats = [c["categoria"] for c in por_categoria[:TOP_HEATMAP]]
    meses = sorted({(int(m["anio"]), int(m["mes"])) for m in cat_mes})
    indices = {c: i for i, c in enumerate(top_cats)}
    indice_mes = {m: i for i, m in enumerate(meses)}
    celdas = [
        [
            indice_mes[(int(m["anio"]), int(m["mes"]))],
            indices[m["categoria"]],
            int(m["total"]),
        ]
        for m in cat_mes
        if m["categoria"] in indices
    ]
    max_celda = max((c[2] for c in celdas), default=0)

    por_tecnico = list(stats.get("por_tecnico") or [])
    asistencias = list(stats.get("asistencias") or [])
    por_mes = list(stats.get("por_mes") or [])

    por_dia = list(stats.get("por_dia") or [])
    calendario = {
        "inicio": por_dia[0]["fecha"] if por_dia else None,
        "fin": por_dia[-1]["fecha"] if por_dia else None,
        "datos": [[d["fecha"], d["total"]] for d in por_dia],
        "max": max((int(d["total"]) for d in por_dia), default=0),
    }

    flujo = list(stats.get("flujo_sankey") or [])
    enlaces: dict[tuple[str, str], int] = {}
    for fl in flujo:
        for origen, destino in (
            (fl["medio"], fl["categoria"]),
            (fl["categoria"], fl["grupo_padre"]),
        ):
            clave = (str(origen), str(destino))
            enlaces[clave] = enlaces.get(clave, 0) + int(fl["total"])
    sankey = {
        "nodos": [{"name": n} for n in {k for par in enlaces for k in par}],
        "links": [
            {"source": o, "target": d, "value": v} for (o, d), v in enlaces.items()
        ],
    }

    tfs = list(stats.get("por_tecnico_fuera") or [])
    scatter = {
        "datos": [
            [
                int(t["total"]),
                int(t["fuera"]),
                str(t["display_name"]),
                round(int(t["fuera"]) * 100 / int(t["total"]), 1)
                if t["total"]
                else 0.0,
            ]
            for t in tfs
        ]
    }

    tcat = list(stats.get("por_tecnico_categoria") or [])
    ejes = [c["categoria"] for c in por_categoria]
    acumulado_tec: dict[tuple[int, str], dict[str, int]] = {}
    for t in tcat:
        clave_tec = (int(t["usuario_id"]), str(t["display_name"]))
        acumulado_tec.setdefault(clave_tec, {})[str(t["categoria"])] = int(t["total"])
    radar = {
        "ejes": ejes,
        "tecnicos": [
            {
                "id": k[0],
                "nombre": k[1],
                "valores": [v.get(c, 0) for c in ejes],
                "total": sum(v.values()),
            }
            for k, v in sorted(
                acumulado_tec.items(), key=lambda kv: -sum(kv[1].values())
            )
        ],
    }

    return {
        "total": total,
        "fuera_de_turno": stats.get("fuera_de_turno", 0),
        "arbol_conteos": {
            "padres": stats.get("por_padre") or [],
            "grupos": stats.get("por_grupo") or [],
            "areas": stats.get("por_area_id") or [],
        },
        "calendario": calendario,
        "sankey": sankey,
        "scatter": scatter,
        "radar": radar,
        "categoria": {
            "labels": [c["categoria"] for c in por_categoria],
            "values": [c["total"] for c in por_categoria],
        },
        "pareto": {
            "labels": [c["categoria"] for c in por_categoria[:TOP_PARETO]],
            "values": [c["total"] for c in por_categoria[:TOP_PARETO]],
            "acumulado": acumulado[:TOP_PARETO],
        },
        "categoria_mes": {
            "categorias": top_cats,
            "meses": [_mes_etiqueta(a, m) for a, m in meses],
            "celdas": celdas,
            "max": max_celda,
        },
        "rendimiento": {
            "labels": [t["display_name"] for t in por_tecnico],
            "values": [t["total"] for t in por_tecnico],
        },
        "colaboraciones": {
            "labels": [t["display_name"] for t in asistencias],
            "values": [t["total"] for t in asistencias],
        },
        "evolucion": {
            "labels": [_mes_etiqueta(int(m["anio"]), int(m["mes"])) for m in por_mes],
            "values": [m["total"] for m in por_mes],
        },
        "medio": {
            "labels": [m["medio"] for m in (stats.get("por_medio") or [])],
            "values": [m["total"] for m in (stats.get("por_medio") or [])],
        },
        "tipo_solicitante": {
            "labels": [t["tipo"] for t in (stats.get("por_tipo_solicitante") or [])],
            "values": [t["total"] for t in (stats.get("por_tipo_solicitante") or [])],
        },
        "top_areas": list(stats.get("por_area") or [])[:10],
    }


def _ficha(
    stats: dict[str, object], scope: dict[str, str], padre: dict[str, object] | None
) -> dict[str, object]:
    total = int(stats.get("total") or 0)
    fuera = int(stats.get("fuera_de_turno") or 0)
    meses = [m for m in (stats.get("por_mes") or []) if int(m["total"]) > 0]
    pico = max(meses, key=lambda m: int(m["total"]), default=None)
    valle = min(meses, key=lambda m: int(m["total"]), default=None)
    cats = sorted((stats.get("por_categoria") or []), key=lambda c: -int(c["total"]))
    top3 = sum(int(c["total"]) for c in cats[:3])
    fuera_pct = round(fuera * 100 / total, 1) if total else 0.0
    pct_padre = None
    delta_padre = None
    if padre is not None:
        ptotal = int(padre.get("total") or 0)
        if ptotal:
            pct_padre = round(total * 100 / ptotal, 1)
            pfuera = int(padre.get("fuera_de_turno") or 0)
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
        "pico": _mes_corto(int(pico["anio"]), int(pico["mes"])) if pico else None,
        "pico_total": int(pico["total"]) if pico else 0,
        "valle": _mes_corto(int(valle["anio"]), int(valle["mes"])) if valle else None,
        "valle_total": int(valle["total"]) if valle else 0,
        "dominante": cats[0]["categoria"] if cats else None,
        "dominante_pct": round(int(cats[0]["total"]) * 100 / total, 1)
        if cats and total
        else 0.0,
        "top3_pct": round(top3 * 100 / total, 1) if total else 0.0,
        "pct_padre": pct_padre,
        "delta_padre": delta_padre,
        "scope": scope,
    }


def _padre_de(stats: dict[str, object]) -> dict[str, int] | None:
    padres = stats.get("por_padre") or []
    if len(padres) == 1:
        return {"total": int(padres[0]["total"])}
    return None


def _payload(request: HttpRequest, token: str) -> dict[str, object]:
    params = _params_stats(request)
    stats = api_get("/api/atenciones/stats", token, params)
    assert isinstance(stats, dict)
    padre_stats: dict[str, int] | None = None
    if params.get("grupo_id") or params.get("area_id"):
        params_padre = {
            k: v for k, v in params.items() if k not in ("grupo_id", "area_id")
        }
        p = api_get("/api/atenciones/stats", token, params_padre)
        if isinstance(p, dict):
            padre_stats = {
                "total": p.get("total", 0),
                "fuera_de_turno": p.get("fuera_de_turno", 0),
            }
    scope = {
        "grupo_padre_id": params.get("grupo_padre_id", ""),
        "grupo_id": params.get("grupo_id", ""),
        "area_id": params.get("area_id", ""),
    }
    return {
        "charts": _graficos(stats),
        "ficha": _ficha(stats, scope, padre_stats),
    }


@con_login
def panel_stats_vista(request: HttpRequest) -> JsonResponse:
    if not _puede_dashboard(request):
        return JsonResponse({"error": "sin permiso"}, status=403)
    return JsonResponse(_payload(request, str(request.session["jwt"])))


@con_login
def dashboard_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    _marcar_sesion(request, True)
    token = str(request.session["jwt"])
    arbol = api_get("/api/jerarquia/arbol", token)
    assert isinstance(arbol, dict)
    datos = _payload(request, token)
    return render(
        request,
        "atenciones/dashboard.html",
        {
            "payload": datos,
            "arbol_json": _json.dumps(arbol),
            "filtros": request.GET,
        },
    )


def _dias_del_mes(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def _params_mes(anio: int, mes: int) -> dict[str, str]:
    return {
        "desde_dia": "1",
        "desde_mes": f"{mes:02d}",
        "desde_anio": str(anio),
        "hasta_dia": str(_dias_del_mes(anio, mes)),
        "hasta_mes": f"{mes:02d}",
        "hasta_anio": str(anio),
    }


def _params_anio(anio: int, mes_fin: int) -> dict[str, str]:
    return {
        "desde_dia": "1",
        "desde_mes": "01",
        "desde_anio": str(anio),
        "hasta_dia": str(_dias_del_mes(anio, mes_fin)),
        "hasta_mes": f"{mes_fin:02d}",
        "hasta_anio": str(anio),
    }


def _periodo_reporte(request: HttpRequest) -> dict[str, object]:
    mes_actual, anio_actual = _mes_actual()
    vista = request.GET.get("vista", "mes").strip()
    if vista not in ("mes", "anio"):
        _log.info("REP-002 vista invalida, se usa mes")
        vista = "mes"
    crudo = request.GET.get("mes", "").strip()
    anio, mes = anio_actual, mes_actual
    valido = (
        len(crudo) == 7
        and crudo[4] == "-"
        and crudo[:4].isdigit()
        and crudo[5:].isdigit()
        and 1 <= int(crudo[5:]) <= 12
    )
    if valido:
        anio, mes = int(crudo[:4]), int(crudo[5:])
    elif crudo:
        _log.info("REP-002 mes invalido, se usa el actual")
    es_mes_en_curso = anio == anio_actual and mes == mes_actual
    etiqueta = (
        f"Acumulado enero–{MESES[mes - 1].lower()} {anio}"
        if vista == "anio"
        else f"{MESES[mes - 1]} {anio}"
    )
    if es_mes_en_curso:
        etiqueta = f"{etiqueta} (parcial)"
    return {
        "vista": vista,
        "mes": f"{anio}-{mes:02d}",
        "anio": anio,
        "mes_num": mes,
        "etiqueta": etiqueta,
        "es_mes_en_curso": es_mes_en_curso,
    }


def _orden_desc(filas: list, clave: str) -> list[dict]:
    return sorted(
        (f for f in filas if isinstance(f, dict)),
        key=lambda f: (-int(f.get("total") or 0), str(f.get(clave, ""))),
    )


def _serie(filas: list[dict], clave: str) -> dict[str, list]:
    return {
        "labels": [str(f.get(clave, "")) for f in filas],
        "values": [int(f.get("total") or 0) for f in filas],
    }


def _evolucion(stats: dict[str, object], anio: int, mes_fin: int) -> dict[str, list]:
    por_mes = {
        int(m["mes"]): int(m["total"])
        for m in (stats.get("por_mes") or [])
        if isinstance(m, dict) and int(m.get("anio") or 0) == anio
    }
    return {
        "labels": [MESES_CORTOS[m - 1] for m in range(1, mes_fin + 1)],
        "values": [por_mes.get(m, 0) for m in range(1, mes_fin + 1)],
    }


def _top_areas(stats: dict[str, object], total: int) -> list[dict[str, object]]:
    filas = _orden_desc(list(stats.get("por_area") or []), "area")[:10]
    return [
        {
            "area": str(f.get("area", "")),
            "total": int(f.get("total") or 0),
            "pct": round(int(f.get("total") or 0) * 100 / total, 1) if total else 0.0,
        }
        for f in filas
    ]


def _kpis_reporte(
    s_mes: dict[str, object],
    s_prev: dict[str, object] | None,
    s_evol: dict[str, object],
    dias: int,
) -> dict[str, object]:
    total = int(s_mes.get("total") or 0)
    fuera = int(s_mes.get("fuera_de_turno") or 0)
    fuera_pct = round(fuera * 100 / total, 1) if total else 0.0
    prev_total = None
    delta_abs = None
    delta_pct = None
    fuera_delta = None
    if s_prev is not None:
        prev_total = int(s_prev.get("total") or 0)
        delta_abs = total - prev_total
        if prev_total:
            delta_pct = round((total - prev_total) * 100 / prev_total, 1)
            prev_fuera = int(s_prev.get("fuera_de_turno") or 0)
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
            1 for m in (s_evol.get("por_mes") or []) if int(m.get("total") or 0) > 0
        ),
    }


def _destacados(
    lista: list[object], mes: str, categorias: list[str]
) -> list[dict[str, object]]:
    del_mes = [
        a
        for a in lista
        if isinstance(a, dict) and str(a.get("fecha_registro") or "")[:7] == mes
    ]
    salida: list[dict[str, object]] = []
    for categoria in categorias:
        candidatos = [a for a in del_mes if a.get("categoria") == categoria]
        if not candidatos:
            continue
        mejor = max(
            candidatos,
            key=lambda a: (len(str(a.get("solucion") or "")), -int(a.get("id") or 0)),
        )
        salida.append(
            {
                "id": int(mejor.get("id") or 0),
                "area": str(mejor.get("area_solicitante") or ""),
                "categoria": str(mejor.get("categoria") or ""),
                "descripcion": str(mejor.get("descripcion") or ""),
                "solucion": str(mejor.get("solucion") or ""),
            }
        )
    return salida


def _metodologia(periodo: dict[str, object]) -> dict[str, str]:
    local = _dt.datetime.now(_dt.UTC).astimezone(_ZONA_LA_PAZ)
    anio = int(periodo["anio"])
    mes = int(periodo["mes_num"])
    inicio = (
        _dt.date(anio, 1, 1) if periodo["vista"] == "anio" else _dt.date(anio, mes, 1)
    )
    fin = _dt.date(anio, mes, _dias_del_mes(anio, mes))
    if periodo["es_mes_en_curso"]:
        corte = f"Datos al {local.strftime('%d/%m/%Y')} — mes en curso, cifras parciales"
    elif periodo["vista"] == "anio":
        corte = f"Acumulado enero–{MESES[mes - 1].lower()} {anio}"
    else:
        corte = "Mes cerrado"
    return {
        "fuente": "GET /api/atenciones/stats",
        "periodo": f"{inicio.strftime('%d/%m/%Y')}–{fin.strftime('%d/%m/%Y')}",
        "generado_en": local.strftime("%d/%m/%Y %H:%M"),
        "corte": corte,
    }


@con_login
def reportes_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        _log.info("REP-001 sin permiso en /reportes/")
        return redirect("atenciones_lista")
    if not request.GET:
        inicial = _periodo_reporte(request)
        return redirect(f"{reverse('reportes')}?mes={inicial['mes']}&vista=mes")
    periodo = _periodo_reporte(request)
    token = str(request.session["jwt"])
    anio = int(periodo["anio"])
    mes = int(periodo["mes_num"])
    vista = str(periodo["vista"])
    try:
        if vista == "anio":
            principal = api_get("/api/atenciones/stats", token, _params_anio(anio, mes))
            previo = None
            stats_evolucion = principal
        else:
            principal = api_get("/api/atenciones/stats", token, _params_mes(anio, mes))
            prev_mes, prev_anio = _mes_vecino(mes, anio, -1)
            previo = api_get(
                "/api/atenciones/stats", token, _params_mes(prev_anio, prev_mes)
            )
            stats_evolucion = api_get(
                "/api/atenciones/stats", token, _params_anio(anio, mes)
            )
    except ApiError as e:
        if e.status in (401, 403):
            raise
        _log.error("REP-003 stats fallo: %s", e.detail)
        return render(
            request,
            "atenciones/reportes.html",
            {"error": True, "payload": None},
            status=502,
        )
    principal = principal if isinstance(principal, dict) else {}
    stats_evolucion = stats_evolucion if isinstance(stats_evolucion, dict) else {}
    previo = previo if isinstance(previo, dict) else None
    total = int(principal.get("total") or 0)
    if total == 0:
        _log.info("REP-005 sin atenciones en el periodo")
    if previo is not None and int(previo.get("total") or 0) == 0 and total > 0:
        _log.info("REP-006 mes previo sin registros, delta s/d")
    dias = (
        (_dt.date(anio, mes, _dias_del_mes(anio, mes)) - _dt.date(anio, 1, 1)).days + 1
        if vista == "anio"
        else _dias_del_mes(anio, mes)
    )
    categorias = _orden_desc(list(principal.get("por_categoria") or []), "categoria")
    destacados: list[dict[str, object]] = []
    destacados_error = False
    if vista == "mes":
        try:
            lista = api_get("/api/atenciones", token, {"limit": "2000"})
        except ApiError as e:
            _log.warning("REP-004 lista fallo: %s", e.detail)
            destacados_error = True
        else:
            destacados = _destacados(
                list(lista) if isinstance(lista, list) else [],
                str(periodo["mes"]),
                [str(c["categoria"]) for c in categorias[:3]],
            )
    charts = {
        "evolucion": _evolucion(stats_evolucion, anio, mes),
        "categoria": _serie(categorias, "categoria"),
        "sectores": _serie(
            _orden_desc(list(principal.get("por_padre") or []), "nombre"), "nombre"
        ),
        "medio": _serie(
            _orden_desc(list(principal.get("por_medio") or []), "medio"), "medio"
        ),
        "tipo_solicitante": _serie(
            _orden_desc(list(principal.get("por_tipo_solicitante") or []), "tipo"),
            "tipo",
        ),
        "top_areas": _top_areas(principal, total),
    }
    payload = {
        "periodo": {
            "vista": periodo["vista"],
            "mes": periodo["mes"],
            "etiqueta": periodo["etiqueta"],
            "es_mes_en_curso": periodo["es_mes_en_curso"],
        },
        "kpis": _kpis_reporte(principal, previo, stats_evolucion, dias),
        "charts": charts,
        "destacados": destacados,
        "metodologia": _metodologia(periodo),
    }
    return render(
        request,
        "atenciones/reportes.html",
        {"payload": payload, "error": False, "destacados_error": destacados_error},
    )


@con_login
def panel_estados_vista(request: HttpRequest) -> JsonResponse:
    if not _puede_dashboard(request):
        return JsonResponse({"error": "sin permiso"}, status=403)
    usuarios = api_get("/api/usuarios", request.session["jwt"])
    assert isinstance(usuarios, list)
    conteo, tecnicos = _presencia(usuarios)
    return JsonResponse({"conteo": conteo, "tecnicos": tecnicos})


PASOS_JERARQUIA = {
    "sector": "grupos-padres",
    "dependencia": "grupos",
    "area": "areas",
}


def _detalle_error(exc: ApiError, por_defecto: str = "No se pudo completar.") -> str:
    return str(exc.detail) if exc.detail else por_defecto


def _parse_nodo(valor: str) -> dict[str, object] | None:
    tipo, _, ident = (valor or "").partition(":")
    if tipo not in PASOS_JERARQUIA or not ident.isdigit():
        return None
    return {"tipo": tipo, "id": int(ident), "clave": f"{tipo}:{ident}"}


def _armar_arbol(arbol: dict, conteos: dict) -> list[dict]:
    def cuenta(lista: str, ident: int) -> int:
        for c in conteos.get(lista) or []:
            if c.get("id") == ident:
                return int(c.get("total") or 0)
        return 0

    areas = [dict(a, total=cuenta("areas", a["id"])) for a in arbol.get("areas") or []]
    grupos = [
        dict(g, total=cuenta("grupos", g["id"])) for g in arbol.get("grupos") or []
    ]
    ramas: list[dict] = []
    for padre in arbol.get("padres") or []:
        suyos = [g for g in grupos if g["grupo_padre_id"] == padre["id"]]
        for grupo in suyos:
            grupo["areas"] = [a for a in areas if a["grupo_id"] == grupo["id"]]
        ramas.append(
            {
                "sector": dict(padre, total=cuenta("padres", padre["id"])),
                "grupos": suyos,
                "directas": [
                    a
                    for a in areas
                    if a["grupo_padre_id"] == padre["id"] and not a["grupo_id"]
                ],
            }
        )
    return ramas


def _detalle(ramas: list[dict], sel: dict | None) -> dict | None:
    if not sel:
        return None
    for rama in ramas:
        sector = rama["sector"]
        if sel["tipo"] == "sector" and sector["id"] == sel["id"]:
            return {
                "tipo": "sector",
                "nodo": sector,
                "sector": sector,
                "dependencia": None,
            }
        for grupo in rama["grupos"]:
            if sel["tipo"] == "dependencia" and grupo["id"] == sel["id"]:
                return {
                    "tipo": "dependencia",
                    "nodo": grupo,
                    "sector": sector,
                    "dependencia": grupo,
                }
            for area in grupo["areas"]:
                if sel["tipo"] == "area" and area["id"] == sel["id"]:
                    return {
                        "tipo": "area",
                        "nodo": area,
                        "sector": sector,
                        "dependencia": grupo,
                    }
        for area in rama["directas"]:
            if sel["tipo"] == "area" and area["id"] == sel["id"]:
                return {
                    "tipo": "area",
                    "nodo": area,
                    "sector": sector,
                    "dependencia": None,
                }
    return None


def _datos_jerarquia(token: str) -> tuple[dict, dict]:
    arbol = api_get("/api/jerarquia/arbol", token, {"incluir_inactivas": "true"})
    stats = api_get("/api/atenciones/stats", token)
    conteos: dict[str, object] = {"padres": [], "grupos": [], "areas": []}
    if isinstance(stats, dict):
        conteos = {
            "padres": stats.get("por_padre") or [],
            "grupos": stats.get("por_grupo") or [],
            "areas": stats.get("por_area_id") or [],
        }
    if not isinstance(arbol, dict):
        arbol = {"padres": [], "grupos": [], "areas": []}
    return arbol, conteos


@con_login
def jerarquia_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    arbol, conteos = _datos_jerarquia(str(request.session["jwt"]))
    ramas = _armar_arbol(arbol, conteos)
    sel = _parse_nodo(request.GET.get("nodo", ""))
    nombre_sector = {r["sector"]["id"]: r["sector"]["nombre"] for r in ramas}
    detalle = _detalle(ramas, sel)
    abrir_grupo = None
    if detalle and detalle["dependencia"]:
        abrir_grupo = detalle["dependencia"]["id"]
    return render(
        request,
        "atenciones/jerarquia.html",
        {
            "ramas": ramas,
            "detalle": detalle,
            "abrir_grupo": abrir_grupo,
            "nodo_sel": sel,
            "destinos_sector": [
                {"valor": f"s:{r['sector']['id']}", "texto": r["sector"]["nombre"]}
                for r in ramas
            ],
            "destinos_grupo": [
                {
                    "valor": f"g:{g['id']}:{r['sector']['id']}",
                    "texto": f"{r['sector']['nombre']} › {g['nombre']}",
                }
                for r in ramas
                for g in r["grupos"]
            ],
            "destino_actual": _destino_actual(detalle),
            "sueltas": [
                dict(a, sector_nombre=nombre_sector.get(a["grupo_padre_id"], "?"))
                for r in ramas
                for a in r["directas"]
            ],
            "ver_sueltas": request.GET.get("sueltas") == "1",
            "flash": request.session.pop("flash", None),
        },
    )


def _destino_actual(detalle: dict | None) -> str:
    if not detalle:
        return ""
    if detalle["dependencia"]:
        return f"g:{detalle['dependencia']['id']}:{detalle['sector']['id']}"
    return f"s:{detalle['sector']['id']}"


def _destino_elegido(request: HttpRequest) -> tuple[int, int | None]:
    """El select manda un solo valor: 's:<sector>' o 'g:<dependencia>:<sector>'."""
    partes = (request.POST.get("destino") or "").split(":")
    if len(partes) == 2 and partes[0] == "s" and partes[1].isdigit():
        return int(partes[1]), None
    if (
        len(partes) == 3
        and partes[0] == "g"
        and partes[1].isdigit()
        and partes[2].isdigit()
    ):
        return int(partes[2]), int(partes[1])
    return 0, None


def _crear_jerarquia(request: HttpRequest, token: str, tipo: str) -> None:
    cuerpo: dict[str, object] = {"nombre": request.POST.get("nombre", "")}
    if tipo in ("dependencia", "area"):
        sector_id, grupo_id = _destino_elegido(request)
        cuerpo["grupo_padre_id"] = sector_id
        if tipo == "area":
            cuerpo["grupo_id"] = grupo_id
    api_post(f"/api/jerarquia/{PASOS_JERARQUIA[tipo]}", token, cuerpo)


def _renombrar_jerarquia(
    request: HttpRequest, token: str, tipo: str, ruta: str, ident: int | None
) -> None:
    cuerpo: dict[str, object] = {"nombre": request.POST.get("nombre", "")}
    if tipo == "area":
        cuerpo["actualizar_texto_legado"] = request.POST.get("texto_legado") == "1"
    api_put(f"{ruta}/{ident}", token, cuerpo)


def _mover_jerarquia(
    request: HttpRequest, token: str, tipo: str, ruta: str, ident: int | None
) -> None:
    sector_id, grupo_id = _destino_elegido(request)
    if tipo == "area":
        api_put(
            f"{ruta}/{ident}",
            token,
            {"grupo_padre_id": sector_id, "grupo_id": grupo_id},
        )
    else:
        api_put(f"{ruta}/{ident}", token, {"grupo_padre_id": sector_id})


@con_login
@require_POST
def jerarquia_accion_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    accion = request.POST.get("accion", "")
    tipo = request.POST.get("tipo", "")
    ident = _int_o_none(request.POST.get("id"))
    volver = request.POST.get("volver", "")
    destino = reverse("jerarquia")
    if volver:
        destino = f"{destino}?nodo={volver}"
    if tipo not in PASOS_JERARQUIA:
        request.session["flash"] = {"tipo": "error", "texto": "Tipo inválido."}
        return redirect(destino)

    ruta = f"/api/jerarquia/{PASOS_JERARQUIA[tipo]}"
    try:
        if accion == "crear":
            _crear_jerarquia(request, token, tipo)
            texto = "Creado."
        elif accion == "renombrar":
            _renombrar_jerarquia(request, token, tipo, ruta, ident)
            texto = "Nombre actualizado."
        elif accion == "mover":
            _mover_jerarquia(request, token, tipo, ruta, ident)
            texto = "Movido. Las atenciones se re-apuntaron."
        elif accion in ("activar", "desactivar"):
            api_put(f"{ruta}/{ident}", token, {"activo": accion == "activar"})
            texto = "Activado." if accion == "activar" else "Desactivado."
        elif accion == "borrar":
            api_delete(f"{ruta}/{ident}", token)
            texto = "Eliminado."
            if volver == f"{tipo}:{ident}":
                destino = reverse("jerarquia")
        else:
            texto = "Acción desconocida."
    except ApiError as e:
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    else:
        request.session["flash"] = {"tipo": "ok", "texto": texto}
    return redirect(destino)


@con_login
def usuarios_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    usuarios = api_get(
        "/api/usuarios", str(request.session["jwt"]), {"incluir_inactivos": "true"}
    )
    lista = usuarios if isinstance(usuarios, list) else []
    return render(
        request,
        "atenciones/usuarios.html",
        {
            "activos": [u for u in lista if u.get("activo")],
            "inactivos": [u for u in lista if not u.get("activo")],
            "roles": ["Tecnico", "Jefe", "Auxiliar"],
            "flash": request.session.pop("flash", None),
            "detalle": request.GET.get("detalle", ""),
        },
    )


@con_login
@require_POST
def usuarios_accion_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    accion = request.POST.get("accion", "")
    ident = _int_o_none(request.POST.get("id"))
    try:
        if accion == "crear":
            cuerpo: dict[str, object] = {
                "email": request.POST.get("email", ""),
                "display_name": request.POST.get("nombre", ""),
                "role": request.POST.get("role", "Tecnico"),
            }
            password = request.POST.get("password", "")
            if password:
                cuerpo["password"] = password
            api_post("/api/usuarios", token, cuerpo)
            texto = "Usuario creado."
        elif accion in ("activar", "desactivar"):
            api_patch(
                f"/api/usuarios/{ident}/activo",
                token,
                {"activo": accion == "activar"},
            )
            texto = "Activado." if accion == "activar" else "Desactivado."
        else:
            texto = "Acción desconocida."
    except ApiError as e:
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    else:
        request.session["flash"] = {"tipo": "ok", "texto": texto}
    return redirect(reverse("usuarios"))


@con_login
def perfil_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    usuario = api_get("/api/usuarios/me", token)
    assert isinstance(usuario, dict)
    sesion = request.session.get("usuario") or {}
    return render(
        request,
        "atenciones/perfil.html",
        {
            "perfil": usuario,
            "email": sesion.get("email", ""),
            "especialidad": usuario.get("especialidad") or "",
            "flash": request.session.pop("flash", None),
        },
    )


@con_login
@require_POST
def perfil_guardar_vista(request: HttpRequest) -> HttpResponse:
    token = str(request.session["jwt"])
    accion = request.POST.get("accion", "")
    usuario_id = (request.session.get("usuario") or {}).get("id")
    texto, error = "", ""
    if accion == "especialidad":
        try:
            api_patch(
                f"/api/usuarios/{usuario_id}/especialidad",
                token,
                {"especialidad": request.POST.get("especialidad", "").strip() or None},
            )
            texto = "Especialidad guardada."
        except ApiError as e:
            error = _detalle_error(e)
    elif accion == "password":
        nueva = request.POST.get("nueva", "")
        if nueva != request.POST.get("repetir", ""):
            error = "Las dos contraseñas nuevas no coinciden."
        else:
            email = str((request.session.get("usuario") or {}).get("email") or "")
            try:
                api_post(
                    "/api/auth/password",
                    token,
                    {"actual": request.POST.get("actual", ""), "nueva": nueva},
                )
                datos = login_api(email, nueva)
                request.session["jwt"] = datos["token"]
                request.session["usuario"] = datos["user"]
                texto = "Contraseña cambiada."
            except ApiError as e:
                error = _detalle_error(e)
    else:
        error = "Acción desconocida."
    request.session["flash"] = {
        "tipo": "error" if error else "ok",
        "texto": error or texto,
    }
    return redirect("perfil")


@con_login
def notas_vista(request: HttpRequest) -> HttpResponse:
    datos = api_get("/api/usuarios/notas", str(request.session["jwt"]))
    contenido = ""
    if isinstance(datos, dict):
        contenido = str(datos.get("contenido") or "")
    return render(request, "atenciones/notas.html", {"contenido": contenido})


@con_login
@require_POST
def notas_guardar_vista(request: HttpRequest) -> JsonResponse:
    try:
        api_put(
            "/api/usuarios/notas",
            str(request.session["jwt"]),
            {"contenido": request.POST.get("contenido", "")},
        )
    except ApiError as e:
        return JsonResponse({"ok": False, "error": _detalle_error(e)}, status=502)
    return JsonResponse({"ok": True})


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

LUNES, SABADO = 1, 6

PLANTILLAS = (
    ("08:00", "16:00", "", ""),
    ("08:00", "12:00", "14:30", "18:30"),
    ("12:00", "20:00", "", ""),
    ("07:00", "15:00", "", ""),
    ("09:00", "17:00", "", ""),
)


def _mes_actual() -> tuple[int, int]:
    local = _dt.datetime.now(_dt.UTC).astimezone(_ZONA_LA_PAZ)
    return local.month, local.year


def _mes_vecino(mes: int, anio: int, delta: int) -> tuple[int, int]:
    indice = (anio * 12 + (mes - 1)) + delta
    return (indice % 12) + 1, indice // 12


def _bloque(fila: dict | None) -> dict[str, str]:
    if not fila:
        return {"h1": "", "f1": "", "h2": "", "f2": "", "label": "Sin horario"}
    return {
        "h1": fila.get("hora_inicio1") or "",
        "f1": fila.get("hora_fin1") or "",
        "h2": fila.get("hora_inicio2") or "",
        "f2": fila.get("hora_fin2") or "",
        "label": fila.get("label") or "Sin horario",
    }


def _franjas_por_tecnico(cobertura: dict, clave: str) -> dict[str, list[str]]:
    """nombre -> bloques que cubre, para ver de un golpe si el escalonado cierra."""
    mapa: dict[str, list[str]] = {}
    for franja in cobertura.get(clave) or []:
        for nombre in franja.get("tecnicos") or []:
            mapa.setdefault(str(nombre), []).append(str(franja.get("franja")))
    return mapa


def _filas_horarios(token: str, mes: int, anio: int) -> list[dict]:
    filas = api_get("/api/horarios", token, {"mes": str(mes), "anio": str(anio)})
    return [f for f in filas if isinstance(f, dict)] if isinstance(filas, list) else []


@con_login
def horarios_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    mes = _int_o_none(request.GET.get("mes")) or _mes_actual()[0]
    anio = _int_o_none(request.GET.get("anio")) or _mes_actual()[1]

    filas = _filas_horarios(token, mes, anio)
    por_persona: dict[int, dict[int, dict]] = {}
    for fila in filas:
        por_persona.setdefault(int(fila["usuario_id"]), {})[int(fila["dia_semana"])] = (
            fila
        )

    usuarios = api_get("/api/usuarios", token)
    personas = (
        [u for u in usuarios if isinstance(u, dict)]
        if isinstance(usuarios, list)
        else []
    )

    cobertura = api_get(
        "/api/horarios/cobertura", token, {"mes": str(mes), "anio": str(anio)}
    )
    cobertura = cobertura if isinstance(cobertura, dict) else {}
    franjas_lv = _franjas_por_tecnico(cobertura, "laborable")
    franjas_sab = _franjas_por_tecnico(cobertura, "sabado")

    def armar(persona: dict) -> dict:
        dias = por_persona.get(int(persona["id"]), {})
        nombre = str(persona["display_name"])
        return {
            "id": persona["id"],
            "nombre": nombre,
            "lv": _bloque(dias.get(LUNES)),
            "sabado": _bloque(dias.get(SABADO)),
            "franjas_lv": franjas_lv.get(nombre, []),
            "franjas_sabado": franjas_sab.get(nombre, []),
            "tiene_horario": bool(dias),
        }
    previo, siguiente = _mes_vecino(mes, anio, -1), _mes_vecino(mes, anio, 1)
    return render(
        request,
        "atenciones/horarios.html",
        {
            "tecnicos": [armar(p) for p in personas if p.get("role") == "Tecnico"],
            "jefes": [armar(p) for p in personas if p.get("role") == "Jefe"],
            "cobertura": cobertura,
            "plantillas": PLANTILLAS,
            "mes": mes,
            "anio": anio,
            "mes_nombre": MESES[mes - 1],
            "mes_previo": previo[0],
            "anio_previo": previo[1],
            "mes_siguiente": siguiente[0],
            "anio_siguiente": siguiente[1],
            "flash": request.session.pop("flash", None),
        },
    )


def _desde_formulario(
    request: HttpRequest, personas: list[dict], mes: int, anio: int, dias: list[int]
) -> tuple[list[dict], list[int]]:
    """Un formulario con todas las filas. Sin horas = sin turno (se borra, no se guarda vacio)."""
    asignaciones: list[dict] = []
    vacios: list[int] = []
    for persona in personas:
        uid = persona["id"]
        horas = [
            request.POST.get(f"u{uid}_{campo}", "").strip()
            for campo in ("h1", "f1", "h2", "f2")
        ]
        if not any(horas):
            vacios.append(uid)
            continue
        base = {
            "usuario_id": uid,
            "mes": mes,
            "anio": anio,
            "hora_inicio1": horas[0] or None,
            "hora_fin1": horas[1] or None,
            "hora_inicio2": horas[2] or None,
            "hora_fin2": horas[3] or None,
        }
        for dia in dias:
            asignaciones.append({**base, "dia_semana": dia})
    return asignaciones, vacios


@con_login
@require_POST
def horarios_guardar_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    mes = _int_o_none(request.POST.get("mes")) or 0
    anio = _int_o_none(request.POST.get("anio")) or 0
    usuarios = api_get("/api/usuarios", token)
    personas = (
        [u for u in usuarios if isinstance(u, dict)]
        if isinstance(usuarios, list)
        else []
    )
    bloque = request.POST.get("bloque")
    if bloque == "jefes":
        personas = [p for p in personas if p.get("role") == "Jefe"]
    else:
        personas = [p for p in personas if p.get("role") == "Tecnico"]
    dias = [SABADO] if bloque == "sabado" else list(range(1, SABADO))
    try:
        asignaciones, vacios = _desde_formulario(request, personas, mes, anio, dias)
        for uid in vacios:
            for dia in dias:
                api_delete(
                    f"/api/horarios?usuario_id={uid}&mes={mes}&anio={anio}"
                    f"&dia_semana={dia}",
                    token,
                )
        if asignaciones:
            api_post("/api/horarios/lote", token, {"asignaciones": asignaciones})
        texto = f"Guardados {len(asignaciones)} turnos."
    except ApiError as e:
        texto = ""
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    else:
        request.session["flash"] = {"tipo": "ok", "texto": texto}
    return redirect(f"{reverse('horarios')}?mes={mes}&anio={anio}")


@con_login
@require_POST
def horarios_limpiar_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    mes = _int_o_none(request.POST.get("mes")) or 0
    anio = _int_o_none(request.POST.get("anio")) or 0
    uid = _int_o_none(request.POST.get("usuario_id")) or 0
    dias = (
        [SABADO] if request.POST.get("bloque") == "sabado" else list(range(1, SABADO))
    )
    try:
        for dia in dias:
            api_delete(
                f"/api/horarios?usuario_id={uid}&mes={mes}&anio={anio}"
                f"&dia_semana={dia}",
                token,
            )
        request.session["flash"] = {"tipo": "ok", "texto": "Horario borrado."}
    except ApiError as e:
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    return redirect(f"{reverse('horarios')}?mes={mes}&anio={anio}")


@con_login
@require_POST
def horarios_copiar_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    mes = _int_o_none(request.POST.get("mes")) or 0
    anio = _int_o_none(request.POST.get("anio")) or 0
    previo_mes, previo_anio = _mes_vecino(mes, anio, -1)
    try:
        filas = _filas_horarios(token, previo_mes, previo_anio)
        if not filas:
            raise ApiError(
                0, f"El mes anterior ({MESES[previo_mes - 1]}) no tiene horarios."
            )
        asignaciones = [
            {
                "usuario_id": f["usuario_id"],
                "dia_semana": f["dia_semana"],
                "mes": mes,
                "anio": anio,
                "hora_inicio1": f.get("hora_inicio1"),
                "hora_fin1": f.get("hora_fin1"),
                "hora_inicio2": f.get("hora_inicio2"),
                "hora_fin2": f.get("hora_fin2"),
            }
            for f in filas
        ]
        api_post("/api/horarios/lote", token, {"asignaciones": asignaciones})
        request.session["flash"] = {
            "tipo": "ok",
            "texto": f"Copiados {len(asignaciones)} horarios de {MESES[previo_mes - 1]}.",
        }
    except ApiError as e:
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    return redirect(f"{reverse('horarios')}?mes={mes}&anio={anio}")


@con_login
@require_POST
def wilmercito_vista(request: HttpRequest) -> JsonResponse:
    try:
        pregunta = _json.loads(request.body).get("pregunta", "").strip()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Pregunta inválida."}, status=400)
    if len(pregunta) < 3:
        return JsonResponse({"ok": False, "error": "Pregunta muy corta."}, status=400)
    try:
        r = api_post(
            "/api/ia/preguntar", str(request.session["jwt"]), {"pregunta": pregunta[:500]}
        )
    except ApiError as e:
        if e.status == 503:
            return JsonResponse(
                {"ok": False, "error": "Wilmercito no disponible ahora mismo."},
                status=503,
            )
        return JsonResponse({"ok": False, "error": _detalle_error(e)}, status=e.status)
    return JsonResponse({"ok": True, **r})


@con_login
@require_POST
def wilmercito_calificar_vista(request: HttpRequest) -> JsonResponse:
    try:
        body = _json.loads(request.body)
    except ValueError:
        return JsonResponse({"ok": False}, status=400)
    try:
        api_post(
            "/api/ia/calificar",
            str(request.session["jwt"]),
            {
                "pregunta": str(body.get("pregunta", ""))[:500],
                "respuesta": str(body.get("respuesta", ""))[:2000],
                "fuente": body.get("fuente"),
                "puntaje": int(body.get("puntaje", 0)),
            },
        )
    except (ApiError, ValueError, TypeError):
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})


@con_login
def conocimiento_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    pendientes = api_get("/api/ia/feedback", str(request.session["jwt"]))
    return render(
        request, "atenciones/conocimiento.html", {"pendientes": pendientes or []}
    )

@con_login
@require_POST
def conocimiento_promover_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    fid = request.POST.get("id", "")
    try:
        api_post(f"/api/ia/feedback/{int(fid)}/promover", str(request.session["jwt"]), {})
    except (ApiError, ValueError):
        pass
    return redirect("conocimiento")


@con_login
def asistente_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    token = str(request.session["jwt"])
    resumen = api_get("/api/ia/resumen", token)
    propuestas = api_get("/api/ia/propuestas", token)
    return render(
        request,
        "atenciones/asistente.html",
        {
            "resumen": resumen if isinstance(resumen, dict) else {},
            "propuestas": propuestas if isinstance(propuestas, list) else [],
            "n_pendientes": 0,
            "flash": request.session.pop("flash", None),
        },
    )


@con_login
@require_POST
def asistente_reindexar_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    try:
        api_post("/api/ia/reindexar", str(request.session["jwt"]), {})
        request.session["flash"] = {"tipo": "ok", "texto": "Índice de Wilmercito actualizado."}
    except ApiError as e:
        request.session["flash"] = {"tipo": "error", "texto": _detalle_error(e)}
    return redirect("asistente")


@con_login
@require_POST
def propuesta_resolver_vista(request: HttpRequest) -> HttpResponse:
    if not _puede_dashboard(request):
        return redirect("atenciones_lista")
    pid = request.POST.get("id", "")
    aprobar = request.POST.get("accion", "") == "aprobar"
    try:
        api_post(
            f"/api/ia/propuestas/{int(pid)}/resolver?aprobar={str(aprobar).lower()}",
            str(request.session["jwt"]),
            {},
        )
        request.session["flash"] = {"tipo": "ok", "texto": "Propuesta resuelta."}
    except (ApiError, ValueError):
        request.session["flash"] = {"tipo": "error", "texto": "No se pudo resolver."}
    return redirect("asistente")
