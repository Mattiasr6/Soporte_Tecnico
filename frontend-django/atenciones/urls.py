from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_vista, name="login"),
    path("logout/", views.logout_vista, name="logout"),
    path("atenciones/", views.lista_vista, name="atenciones_lista"),
]
