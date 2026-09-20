from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio_vista, name="inicio"),
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
    path("panel/estados/", views.panel_estados_vista, name="panel_estados"),
    path("auxiliares/", views.auxiliares_vista, name="auxiliares"),
]
