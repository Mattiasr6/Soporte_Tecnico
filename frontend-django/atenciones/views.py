import datetime as _dt
import json as _json

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .api import ApiError, api_get, api_post, login_api
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


def login_vista(request: HttpRequest) -> HttpResponse:
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
                return redirect("atenciones_lista")
            except ApiError as e:
                error = str(e.detail) if e.detail else "No se pudo entrar"
    else:
        form = LoginForm()
    return render(request, "atenciones/login.html", {"form": form, "error": error})


def logout_vista(request: HttpRequest) -> HttpResponse:
    request.session.flush()
    return redirect("login")


@con_login
def lista_vista(request: HttpRequest) -> HttpResponse:
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
        },
    )


@con_login
def nueva_vista(request: HttpRequest) -> HttpResponse:
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
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()
