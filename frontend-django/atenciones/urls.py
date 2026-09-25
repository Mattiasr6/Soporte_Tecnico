from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio_vista, name="inicio"),
    path("inicio/estado/", views.inicio_estado_vista, name="inicio_estado"),
    path("inicio/anuncio/", views.inicio_anuncio_vista, name="inicio_anuncio"),
    path(
        "inicio/anuncio/guardar/",
        views.inicio_anuncio_guardar_vista,
        name="inicio_anuncio_guardar",
    ),
    path("login/", views.login_vista, name="login"),
    path("logout/", views.logout_vista, name="logout"),
    path("atenciones/", views.lista_vista, name="atenciones_lista"),
    path("atenciones/nueva/", views.nueva_vista, name="atenciones_nueva"),
    path(
        "atenciones/<int:atencion_id>/ticket/",
        views.ticket_vista,
        name="atencion_ticket",
    ),
    path(
        "atenciones/<int:atencion_id>/editar/",
        views.atencion_editar_vista,
        name="atencion_editar",
    ),
    path(
        "atenciones/<int:atencion_id>/eliminar/",
        views.atencion_eliminar_vista,
        name="atencion_eliminar",
    ),
    path("dashboard/", views.dashboard_vista, name="dashboard"),
    path("reportes/", views.reportes_vista, name="reportes"),
    path("jerarquia/", views.jerarquia_vista, name="jerarquia"),
    path("jerarquia/accion/", views.jerarquia_accion_vista, name="jerarquia_accion"),
    path("usuarios/", views.usuarios_vista, name="usuarios"),
    path("usuarios/accion/", views.usuarios_accion_vista, name="usuarios_accion"),
    path("panel/estados/", views.panel_estados_vista, name="panel_estados"),
    path("panel/stats/", views.panel_stats_vista, name="panel_stats"),
    path("horarios/", views.horarios_vista, name="horarios"),
    path("horarios/guardar/", views.horarios_guardar_vista, name="horarios_guardar"),
    path("horarios/limpiar/", views.horarios_limpiar_vista, name="horarios_limpiar"),
    path("horarios/copiar/", views.horarios_copiar_vista, name="horarios_copiar"),
    path("perfil/", views.perfil_vista, name="perfil"),
    path("perfil/guardar/", views.perfil_guardar_vista, name="perfil_guardar"),
    path("notas/", views.notas_vista, name="notas"),
    path("notas/guardar/", views.notas_guardar_vista, name="notas_guardar"),
    path("auxiliares/", views.auxiliares_vista, name="auxiliares"),
    path("wilmercito/", views.wilmercito_vista, name="wilmercito"),
    path(
        "wilmercito/calificar/",
        views.wilmercito_calificar_vista,
        name="wilmercito_calificar",
    ),
    path("conocimiento/", views.conocimiento_vista, name="conocimiento"),
    path(
        "conocimiento/promover/",
        views.conocimiento_promover_vista,
        name="conocimiento_promover",
    ),
    path("asistente/", views.asistente_vista, name="asistente"),
    path(
        "asistente/reindexar/",
        views.asistente_reindexar_vista,
        name="asistente_reindexar",
    ),
]
