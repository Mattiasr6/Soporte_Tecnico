from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .api import ApiError, api_get, login_api
from .auth import con_login
from .forms import LoginForm


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
