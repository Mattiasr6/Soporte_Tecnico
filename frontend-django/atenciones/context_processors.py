"""Expone sesión a templates: usuario, página activa y permisos de nav."""

from django.conf import settings

ASSETS = (
    "css/tokens.css",
    "css/navbar.css",
    "js/navbar.js",
    "js/jerarquia.js",
    "js/dashboard.js",
    "js/inicio.js",
    "js/reportes.js",
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
        "lab_lista": "laboratorios",
        "lab_nueva": "lab_nueva",
        "lab_editar": "laboratorios",
        "lab_eliminar": "laboratorios",
        "lab_reportes": "lab_reportes",
        "lab_dashboard": "lab_dashboard",
        "lab_export_csv": "laboratorios",
        "auxiliares": "auxiliares",
        "auxiliares_horarios": "auxiliares_horarios",
        "auxiliares_sabados": "auxiliares_horarios",
        "auxiliares_soy": "auxiliares",
        "novedades": "novedades",
        "novedad_foto": "novedades",
        "horarios_export_xlsx": "auxiliares_horarios",
        "horarios_export_pdf": "auxiliares_horarios",
        "dashboard": "dashboard",
        "reportes": "reportes",
        "jerarquia": "jerarquia",
        "perfil": "perfil",
        "notas": "notas",
        "sugerencias": "sugerencias",
        "horarios": "horarios",
        "usuarios": "usuarios",
        "asistente": "asistente",
        "conocimiento": "conocimiento",
    }.get(url_name or "", "")
    rol = (usuario or {}).get("role", "")
    can_dashboard = rol == "Jefe" or bool((usuario or {}).get("can_view_dashboard"))
    es_auxiliar = rol == "Auxiliar"
    es_encargado = rol == "Encargado"
    # OJO: matchear sobre url_name (lab_lista, lab_nueva...), NO sobre pagina
    # mapeada ("laboratorios" no empieza con lab_ y rompe el sistema).
    _es_lab = (url_name or "").startswith("lab_")
    if pagina in ("auxiliares", "auxiliares_horarios", "auxiliares_soy", "horarios_export_xlsx", "horarios_export_pdf", "novedades") or _es_lab:
        sistema = "AUXILIARES"
    elif pagina == "sugerencias" and request.session.get("sistema_panel") in ("SOPORTE", "AUXILIARES"):
        sistema = request.session["sistema_panel"]
    else:
        sistema = "AUXILIARES" if es_auxiliar else "SOPORTE"
    return {
        "usuario": usuario,
        "auxiliar_nombre": request.session.get("auxiliar_nombre", ""),
        "nav_page": pagina,
        "can_dashboard": can_dashboard,
        "es_auxiliar": es_auxiliar,
        "es_encargado": es_encargado,
        "sistema": sistema,
        "asset_version": asset_version(),
    }
