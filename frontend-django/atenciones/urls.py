from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio_vista, name="inicio"),
    path("login/", views.login_vista, name="login"),
    path("logout/", views.logout_vista, name="logout"),
    path("atenciones/", views.lista_vista, name="atenciones_lista"),
    path("atenciones/nueva/", views.nueva_vista, name="atenciones_nueva"),
    path("auxiliares/", views.auxiliares_vista, name="auxiliares"),
]
