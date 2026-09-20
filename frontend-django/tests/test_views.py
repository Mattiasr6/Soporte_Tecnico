"""Tests S9: vistas Django con FastAPI mockeado."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from unittest.mock import patch  # noqa: E402

from django.conf import settings as _settings  # noqa: E402
from django.test import Client, TestCase  # noqa: E402

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

ATENCIONES = [
    {
        "id": 9,
        "usuario_id": 2,
        "usuario_nombre": "Diego Orihuela Herrera",
        "area_solicitante": "Biblioteca",
        "grupo_padre_id": 2,
        "grupo_padre_nombre": "Académicos",
        "grupo_id": 3,
        "grupo_nombre": "Biblioteca",
        "area_id": 40,
        "area_nombre": "Biblioteca",
        "medio_solicitud": "Interno",
        "usuario_solicitante": "ADM",
        "categoria": "Hardware",
        "descripcion": "PC sin red",
        "solucion": "Se cambió patchcord",
        "observaciones": None,
        "enlace_apoyo": None,
        "colaborador_id": None,
        "colaborador_nombre": None,
        "fecha_registro": "2026-09-01",
        "fuera_de_turno": True,
        "created_at": "2026-09-01T10:00:00Z",
    }
]

STATS = {
    "total": 12,
    "fuera_de_turno": 2,
    "por_tecnico": [{"usuario_id": 2, "display_name": "Diego", "total": 7}],
    "por_categoria": [{"categoria": "Impresión", "total": 5}],
    "por_mes": [{"anio": 2026, "mes": 9, "total": 12}],
    "por_area": [{"area": "Sistemas", "total": 4}],
    "por_medio": [{"medio": "Interno", "total": 12}],
    "por_categoria_mes": [
        {"categoria": "Impresión", "anio": 2026, "mes": 9, "total": 5}
    ],
    "asistencias": [{"usuario_id": 3, "display_name": "Paul", "total": 2}],
}

TECNICO = {
    "id": 2,
    "display_name": "Diego",
    "role": "Tecnico",
    "can_view_dashboard": False,
}
MATTIAS = {
    "id": 1,
    "display_name": "Mattias",
    "role": "Tecnico",
    "can_view_dashboard": True,
}
JEFE = {"id": 8, "display_name": "Jefe", "role": "Jefe", "can_view_dashboard": True}
AUXILIAR = {
    "id": 10,
    "display_name": "Auxiliar Soporte",
    "role": "Auxiliar",
    "can_view_dashboard": False,
}


class VistasTest(TestCase):
    def setUp(self):
        self._como(TECNICO)

    def _como(self, usuario):
        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = usuario
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key

    def test_login_get(self):
        self.client.session.flush()
        r = Client().get("/login/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "data-navbar")

    def test_login_redirige_si_hay_sesion(self):
        self.assertRedirects(
            self.client.get("/login/"), "/atenciones/", fetch_redirect_response=False
        )
        self._como(AUXILIAR)
        self.assertRedirects(
            self.client.get("/login/"), "/auxiliares/", fetch_redirect_response=False
        )

    @patch("atenciones.views.api_get")
    def test_lista(self, mock_get):
        mock_get.return_value = []
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Mostrando 0 registros")
        self.assertContains(r, "data-navbar")
        self.assertContains(r, "Soporte")
        self.assertNotContains(r, "Dashboard")
        self.assertNotContains(r, "data-system-view")

    def test_lista_sin_login(self):
        self.client.session.flush()
        r = Client().get("/atenciones/")
        self.assertEqual(r.status_code, 302)

    @patch("atenciones.views.api_get")
    def test_navbar_jefe(self, mock_get):
        self._como(JEFE)
        mock_get.return_value = []
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Dashboard")
        self.assertContains(r, "SOPORTE")
        self.assertContains(r, 'data-sistema-panel="SOPORTE"')
        self.assertContains(r, "Próximamente sidebar completo para auxiliares")

    @patch("atenciones.views.api_get")
    def test_navbar_can_view_dashboard(self, mock_get):
        self._como(MATTIAS)
        mock_get.return_value = []
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "data-system-view")
        self.assertContains(r, "Dashboard")

    def test_navbar_auxiliar(self):
        self._como(AUXILIAR)
        r = self.client.get("/auxiliares/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-sistema="AUXILIARES"')
        self.assertContains(r, "Próximamente apartado completo para auxiliares")
        self.assertNotContains(r, "data-system-view")
        self.assertNotContains(r, "Dashboard")
        self.assertContains(r, 'data-sistema-panel="SOPORTE" hidden')

    def test_auxiliar_fuera_de_soporte(self):
        self._como(AUXILIAR)
        self.assertRedirects(
            self.client.get("/atenciones/"),
            "/auxiliares/",
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get("/atenciones/nueva/"),
            "/auxiliares/",
            fetch_redirect_response=False,
        )

    def test_tecnico_no_entra_a_auxiliares(self):
        self.assertRedirects(
            self.client.get("/auxiliares/"),
            "/atenciones/",
            fetch_redirect_response=False,
        )

    @patch("atenciones.views.api_get")
    def test_jefe_entra_a_auxiliares(self, mock_get):
        self._como(JEFE)
        mock_get.return_value = []
        r = self.client.get("/auxiliares/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'data-sistema="AUXILIARES"')
        self.assertContains(r, "data-system-view")
        self.assertContains(r, 'data-url-auxiliares="/auxiliares/"')
        self.assertContains(r, 'data-sistema-panel="SOPORTE" hidden')

    def test_inicio_rutea_por_rol(self):
        self.assertRedirects(
            self.client.get("/"), "/atenciones/", fetch_redirect_response=False
        )
        self._como(AUXILIAR)
        self.assertRedirects(
            self.client.get("/"), "/auxiliares/", fetch_redirect_response=False
        )

    def test_inicio_sin_sesion(self):
        self.client.session.flush()
        self.assertRedirects(
            Client().get("/"), "/login/", fetch_redirect_response=False
        )

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

    # --- modal de ticket ---

    @patch("atenciones.views.api_get")
    def test_ticket_dueno_puede_editar_y_eliminar(self, mock_get):
        mock_get.side_effect = [ATENCIONES, ARBOL, USUARIOS]
        r = self.client.get("/atenciones/9/ticket/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "#9")
        self.assertContains(r, "Biblioteca")
        self.assertContains(r, "data-editar")
        self.assertContains(r, "ticket-edit")
        self.assertContains(r, "/atenciones/9/eliminar/")

    @patch("atenciones.views.api_get")
    def test_ticket_ajeno_solo_lectura(self, mock_get):
        self._como({"id": 3, "display_name": "Paul", "role": "Tecnico"})
        mock_get.side_effect = [ATENCIONES]
        r = self.client.get("/atenciones/9/ticket/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "data-editar")
        self.assertNotContains(r, "/atenciones/9/eliminar/")

    @patch("atenciones.views.api_get")
    def test_ticket_jefe_no_edita_ni_elimina(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = [ATENCIONES]
        r = self.client.get("/atenciones/9/ticket/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "data-editar")
        self.assertNotContains(r, "/atenciones/9/eliminar/")

    @patch("atenciones.views.api_get")
    def test_ticket_inexistente_404(self, mock_get):
        mock_get.return_value = ATENCIONES
        self.assertEqual(self.client.get("/atenciones/12345/ticket/").status_code, 404)

    @patch("atenciones.views.api_get")
    @patch("atenciones.views.api_put")
    def test_editar_guardar(self, mock_put, mock_get):
        mock_get.return_value = []
        mock_put.return_value = None
        r = self.client.post(
            "/atenciones/9/editar/",
            {
                "area_id": "1",
                "medio_solicitud": "Interno",
                "usuario_solicitante": "ADM",
                "categoria": "Hardware",
                "descripcion": "D",
                "solucion": "S",
                "fecha_registro": "2026-01-15",
                "colaborador_id": "2",
            },
        )
        self.assertRedirects(r, "/atenciones/", fetch_redirect_response=False)
        body = mock_put.call_args[0][2]
        self.assertEqual(body["area_id"], 1)
        self.assertEqual(body["colaborador_id"], 2)
        self.assertEqual(body["fecha_registro"], "2026-01-15")

    @patch("atenciones.views.api_get")
    @patch("atenciones.views.api_delete")
    def test_eliminar(self, mock_delete, mock_get):
        mock_get.return_value = []
        mock_delete.return_value = None
        r = self.client.post("/atenciones/9/eliminar/")
        self.assertRedirects(r, "/atenciones/", fetch_redirect_response=False)
        mock_delete.assert_called_once()

    @patch("atenciones.views.api_get")
    def test_lista_muestra_ojo(self, mock_get):
        mock_get.return_value = ATENCIONES
        r = self.client.get("/atenciones/")
        self.assertContains(r, 'data-ver="9"')
        self.assertContains(r, "modal-ticket")

    # --- dashboard ---

    @patch("atenciones.views.api_get")
    def test_dashboard_jefe(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = [USUARIOS, ARBOL, STATS]
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Casos por categoría")
        self.assertContains(r, "Presencia en vivo")
        self.assertContains(r, "Casos por día")
        self.assertContains(r, "Ficha del scope")
        self.assertContains(r, "Top 10 áreas")
        self.assertIn("ficha", r.context["payload"])
        self.assertEqual(r.context["payload"]["ficha"]["casos"], STATS["total"])

    def test_dashboard_tecnico_redirige(self):
        self.assertRedirects(
            self.client.get("/dashboard/"),
            "/atenciones/",
            fetch_redirect_response=False,
        )

    @patch("atenciones.views.api_get")
    def test_dashboard_pasa_filtros(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = [USUARIOS, ARBOL, STATS, STATS]
        r = self.client.get(
            "/dashboard/?grupo_padre_id=1&desde=2026-01&hasta=2026-09&area_id=28"
        )
        self.assertEqual(r.status_code, 200)
        llamadas = [
            c for c in mock_get.call_args_list if c[0][0] == "/api/atenciones/stats"
        ]
        self.assertEqual(len(llamadas), 2, "scope + padre para el delta")
        params = llamadas[0][0][2]
        self.assertEqual(params["grupo_padre_id"], "1")
        self.assertEqual(params["area_id"], "28")
        self.assertEqual(params["desde_anio"], "2026")
        self.assertEqual(params["desde_mes"], "01")
        self.assertEqual(params["hasta_mes"], "09")
        self.assertNotIn("area_id", llamadas[1][0][2])
        self.assertEqual(r.context["payload"]["ficha"]["pct_padre"], 100.0)

    @patch("atenciones.views.api_get")
    def test_panel_stats_json(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = [STATS, STATS]
        r = self.client.get("/panel/stats/?area_id=28")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(set(d), {"charts", "ficha"})
        self.assertIn("calendario", d["charts"])
        self.assertIn("sankey", d["charts"])
        self.assertIn("scatter", d["charts"])
        self.assertIn("radar", d["charts"])
        self.assertEqual(d["ficha"]["casos"], STATS["total"])
        self.assertEqual(
            d["ficha"]["fuera_pct"],
            round(STATS["fuera_de_turno"] * 100 / STATS["total"], 1),
        )

    @patch("atenciones.views.api_get")
    def test_panel_estados_json(self, mock_get):
        self._como(JEFE)
        mock_get.return_value = USUARIOS
        r = self.client.get("/panel/estados/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("conteo", data)
        self.assertEqual(data["conteo"]["ausente"], 1)
        self.assertEqual(len(data["tecnicos"]), 1)

    def test_panel_estados_sin_permiso(self):
        r = self.client.get("/panel/estados/")
        self.assertEqual(r.status_code, 403)
