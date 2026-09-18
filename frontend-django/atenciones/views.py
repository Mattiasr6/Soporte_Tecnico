from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .api import ApiError, login_api
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
