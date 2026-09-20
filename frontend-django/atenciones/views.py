import contextlib
import datetime as _dt
import json as _json

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .api import (
    ApiError,
    api_delete,
    api_get,
    api_post,
    api_put,
    login_api,
)
from .auth import con_login
from .forms import LoginForm

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
    return "auxiliares" if _es_auxiliar(request) else "atenciones_lista"


def inicio_vista(request: HttpRequest) -> HttpResponse:
    if not request.session.get("jwt"):
        return redirect("login")
    return redirect(_destino(request))


def logout_vista(request: HttpRequest) -> HttpResponse:
    _marcar_sesion(request, False)
    request.session.flush()
    return redirect("login")


@con_login
def lista_vista(request: HttpRequest) -> HttpResponse:
    if _es_auxiliar(request):
        return redirect("auxiliares")
    token = request.session["jwt"]
    usuario = request.session["usuario"]
    q = request.GET.get("q", "").strip().lower()
    categoria = request.GET.get("categoria", "").strip()
    mes = request.GET.get("mes", "").strip()
    data = api_get("/api/atenciones", token)
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
    return render(
        request,
        "atenciones/lista.html",
        {
            "atenciones": filas,
            "total": len(filas),
            "usuario": usuario,
            "q": request.GET.get("q", ""),
            "categoria": categoria,
            "mes": mes,
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
    recientes = api_get("/api/atenciones", token)
    assert isinstance(arbol, dict) and isinstance(usuarios, list)
    assert isinstance(recientes, list)
    return render(
        request,
        "atenciones/nueva.html",
        {
            "arbol_json": _json.dumps(arbol),
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


def _presencia(
    usuarios: list[object],
) -> tuple[dict[str, int], list[dict[str, object]]]:
    conteo = {"disponible": 0, "ocupado": 0, "extraturno": 0, "ausente": 0}
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
            }
        )
    tecnicos.sort(key=lambda t: (str(t["estado"]) != "disponible", str(t["nombre"])))
    return conteo, tecnicos


def _mes_etiqueta(anio: int, mes: int) -> str:
    return f"{anio}-{mes:02d}"


MESES_CORTOS = (
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
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
    usuarios = api_get("/api/usuarios", token)
    arbol = api_get("/api/jerarquia/arbol", token)
    assert isinstance(usuarios, list) and isinstance(arbol, dict)
    conteo, tecnicos = _presencia(usuarios)
    datos = _payload(request, token)
    return render(
        request,
        "atenciones/dashboard.html",
        {
            "payload": datos,
            "arbol_json": _json.dumps(arbol),
            "conteo": conteo,
            "tecnicos": tecnicos,
            "filtros": request.GET,
        },
    )


@con_login
def panel_estados_vista(request: HttpRequest) -> JsonResponse:
    if not _puede_dashboard(request):
        return JsonResponse({"error": "sin permiso"}, status=403)
    usuarios = api_get("/api/usuarios", request.session["jwt"])
    assert isinstance(usuarios, list)
    conteo, tecnicos = _presencia(usuarios)
    return JsonResponse({"conteo": conteo, "tecnicos": tecnicos})
