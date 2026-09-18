from collections.abc import Callable
from functools import wraps

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from .api import ApiError


def con_login(vista: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(vista)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.session.get("jwt"):
            return redirect("login")
        try:
            return vista(request, *args, **kwargs)
        except ApiError as e:
            if e.status in (401, 403):
                request.session.flush()
                return redirect("login")
            raise

    return wrapper
