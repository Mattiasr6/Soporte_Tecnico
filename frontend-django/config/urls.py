from django.urls import include, path

urlpatterns = [
    path("", include("atenciones.urls")),
]
