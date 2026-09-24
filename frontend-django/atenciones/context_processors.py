"""Expone sesión a templates: usuario, página activa y permisos de nav."""

from django.conf import settings

ASSETS = (
    "css/tokens.css",
    "css/navbar.css",
    "js/navbar.js",
    "js/jerarquia.js",
    "js/dashboard.js",
    "js/inicio.js",
)


def asset_version() -> int:
    version = 0
    for raiz in settings.STATICFILES_DIRS:
        for nombre in ASSETS:
            ruta = raiz / nombre
            if ruta.exists():
                version = max(version, int(ruta.stat().st_mtime))
    return version


def sesion(request):
    usuario = request.session.get("usuario")
    if not isinstance(usuario, dict):
        usuario = None
    try:
        url_name = request.resolver_match.url_name
    except AttributeError:
        url_name = None
    pagina = {
        "inicio": "inicio",
        "login": "login",
        "atenciones_lista": "lista",
        "atenciones_nueva": "nueva",
        "auxiliares": "auxiliares",
        "dashboard": "dashboard",
        "jerarquia": "jerarquia",
        "perfil": "perfil",
        "notas": "notas",
        "horarios": "horarios",
        "usuarios": "usuarios",
    }.get(url_name or "", "")
    rol = (usuario or {}).get("role", "")
    can_dashboard = rol == "Jefe" or bool((usuario or {}).get("can_view_dashboard"))
    es_auxiliar = rol == "Auxiliar"
    sistema = "AUXILIARES" if (es_auxiliar or pagina == "auxiliares") else "SOPORTE"
    return {
        "usuario": usuario,
        "nav_page": pagina,
        "can_dashboard": can_dashboard,
        "es_auxiliar": es_auxiliar,
        "sistema": sistema,
        "asset_version": asset_version(),
    }
