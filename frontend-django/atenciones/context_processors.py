"""Expone sesión a templates: usuario, página activa y permisos de nav."""


def sesion(request):
    usuario = request.session.get("usuario")
    if not isinstance(usuario, dict):
        usuario = None
    try:
        url_name = request.resolver_match.url_name
    except AttributeError:
        url_name = None
    pagina = {
        "login": "login",
        "atenciones_lista": "lista",
        "atenciones_nueva": "nueva",
    }.get(url_name or "", "")
    rol = (usuario or {}).get("role", "")
    can_dashboard = rol == "Jefe" or bool((usuario or {}).get("can_view_dashboard"))
    sistema = "AUXILIARES" if rol == "Auxiliar" else "SOPORTE"
    return {
        "usuario": usuario,
        "nav_page": pagina,
        "can_dashboard": can_dashboard,
        "sistema": sistema,
    }
