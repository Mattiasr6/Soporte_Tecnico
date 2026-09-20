"""Tests S9: vistas Django con FastAPI mockeado."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from unittest.mock import patch

from django.test import Client, TestCase

ARBOL = {
    "padres": [{"id": 1, "nombre": "Administrativos", "descripcion": None, "orden": 1}],
    "grupos": [{"id": 1, "grupo_padre_id": 1, "nombre": "G", "activo": True}],
    "areas": [
        {
            "id": 1,
            "grupo_padre_id": 1,
            "grupo_id": 1,
            "nombre": "Biblioteca",
            "activo": True,
        }
    ],
}
USUARIOS = [
    {"id": 1, "display_name": "M", "role": "Tecnico", "estado_actual": "ausente"}
]


class VistasTest(TestCase):
    def setUp(self):
        from django.conf import settings as _settings

        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = {"id": 1}
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key

    def test_login_get(self):
        self.client.session.flush()
        r = Client().get("/login/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "data-navbar")

    @patch("atenciones.views.api_get")
    def test_lista(self, mock_get):
        mock_get.return_value = []
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Mostrando 0 registros")
        self.assertContains(r, "data-navbar")
        self.assertContains(r, "Soporte")
        self.assertNotContains(r, "Dashboard")

    @patch("atenciones.views.api_get")
    def test_navbar_jefe(self, mock_get):
        from django.conf import settings as _settings

        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = {
            "id": 8,
            "display_name": "Jefe",
            "role": "Jefe",
            "can_view_dashboard": True,
        }
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key
        mock_get.return_value = []
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Dashboard")
        self.assertContains(r, "SOPORTE")

    def test_lista_sin_login(self):
        self.client.session.flush()
        r = Client().get("/atenciones/")
        self.assertEqual(r.status_code, 302)

    @patch("atenciones.views.api_get")
    def test_nueva_get(self, mock_get):
        mock_get.side_effect = [ARBOL, USUARIOS, []]
        r = self.client.get("/atenciones/nueva/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Colaborador")

    @patch("atenciones.views.api_get")
    @patch("atenciones.views.api_post")
    def test_nueva_agregar_y_enviar(self, mock_post, mock_get):
        mock_get.side_effect = [ARBOL, USUARIOS, []]
        item = {
            "action": "agregar",
            "area_id": "1",
            "grupo_padre_id": "1",
            "grupo_id": "1",
            "medio_solicitud": "Interno",
            "usuario_solicitante": "ADM",
            "categoria": "Hardware",
            "descripcion": "D",
            "solucion": "S",
            "fecha_registro": "2026-09-18",
        }
        r = self.client.post("/atenciones/nueva/", item)
        self.assertEqual(r.status_code, 302)
        mock_post.return_value = {"registros_insertados": 1}
        r = self.client.post("/atenciones/nueva/", {"action": "enviar"})
        self.assertRedirects(r, "/atenciones/", fetch_redirect_response=False)
        mock_post.assert_called_once()
        body = mock_post.call_args[0][2]
        self.assertEqual(body["atenciones"][0]["area_id"], 1)
        self.assertEqual(body["atenciones"][0]["fecha_registro"], "2026-09-18")
