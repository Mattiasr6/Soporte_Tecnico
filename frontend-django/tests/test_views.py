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

YO = {
    "id": 2,
    "display_name": "M",
    "role": "Tecnico",
    "estado_actual": "disponible",
    "horario_hoy": "11:00-19:00",
    "entra_a_las": None,
    "atenciones_hoy": 3,
    "puede_cambiar_estado": True,
}

ANUNCIO = {"message": "Corte de red 15-16", "author": "Josue", "at": "09:12"}

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
            self.client.get("/login/"), "/", fetch_redirect_response=False
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
        self.assertContains(r, "Mostrando 0 de 0 registros")
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

    @patch("atenciones.views.api_get")
    def test_inicio_rutea_por_rol(self, mock_get):
        mock_get.side_effect = [USUARIOS, YO, ANUNCIO]
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El equipo ahora")
        self.assertContains(r, ANUNCIO["message"])
        self._como(AUXILIAR)
        self.assertRedirects(
            self.client.get("/"), "/auxiliares/", fetch_redirect_response=False
        )

    @patch("atenciones.views.api_get")
    def test_inicio_accesos_segun_permiso(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = [USUARIOS, YO, ANUNCIO]
        r = self.client.get("/")
        self.assertContains(r, 'class="acceso" href="/dashboard/"')
        self.assertContains(r, 'class="acceso" href="/jerarquia/"')
        self._como(TECNICO)
        mock_get.side_effect = [USUARIOS, YO, ANUNCIO]
        r = self.client.get("/")
        self.assertNotContains(r, 'class="acceso" href="/dashboard/"')
        self.assertNotContains(r, 'class="acceso" href="/jerarquia/"')
        self.assertContains(r, 'class="acceso" href="/atenciones/nueva/"')

    @patch("atenciones.views.api_get")
    def test_inicio_estado_fuera_de_turno_deshabilita(self, mock_get):
        fuera = dict(YO, estado_actual="extraturno", puede_cambiar_estado=False)
        equipo = [dict(USUARIOS[0], estado_actual="extraturno")]
        mock_get.side_effect = [equipo, fuera, ANUNCIO]
        r = self.client.get("/")
        self.assertContains(r, 'data-puede-estado="0"')
        self.assertContains(r, 'id="mi-estado-chip">Fuera de turno<')
        self.assertContains(r, 'class="estado estado-extraturno">Fuera de turno</span>')

    def test_inicio_sin_sesion(self):
        self.client.session.flush()
        self.assertRedirects(
            Client().get("/"), "/login/", fetch_redirect_response=False
        )

    @patch("atenciones.views.api_get")
    def test_nueva_no_desloguea_al_tecnico(self, mock_get):
        """El stats es solo para jefes. Cuando un tecnico abre 'Soporte', ese 401 no puede
        matarle la sesion: antes lo mandaba al login en vez de al formulario."""
        from atenciones.api import ApiError

        def responder(path, *args, **kwargs):
            if path == "/api/atenciones/stats":
                raise ApiError(401, "Sin permiso")
            if path == "/api/jerarquia/arbol":
                return ARBOL
            if path == "/api/usuarios":
                return USUARIOS
            return []

        mock_get.side_effect = responder
        r = self.client.get("/atenciones/nueva/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Colaborador")

    @patch("atenciones.views.api_get")
    def test_nueva_get(self, mock_get):
        mock_get.side_effect = [ARBOL, USUARIOS, [], STATS]
        r = self.client.get("/atenciones/nueva/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Colaborador")
        self.assertContains(r, "arbol")
        self.assertIn("conteos_json", r.context)

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
    def test_lista_pagina_de_a_50(self, mock_get):
        self._como(JEFE)
        muchas = [dict(ATENCIONES[0], id=i) for i in range(60)]
        mock_get.return_value = muchas

        r = self.client.get("/atenciones/")
        self.assertEqual(len(r.context["atenciones"]), 50)
        self.assertTrue(r.context["hay_mas"])
        self.assertEqual(r.context["restantes"], 10)
        self.assertContains(r, "Ver más")
        self.assertContains(r, "Mostrando 50 de 60 registros")

        r2 = self.client.get("/atenciones/?limite=100")
        self.assertEqual(len(r2.context["atenciones"]), 60)
        self.assertFalse(r2.context["hay_mas"])
        self.assertNotContains(r2, "Ver más")

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
        mock_get.side_effect = [ARBOL, STATS]
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Casos por categoría")
        self.assertContains(r, "Casos por día")
        self.assertContains(r, "Resumen del filtro")
        self.assertContains(r, "Top 10 áreas")
        self.assertNotContains(r, "Presencia en vivo")
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
        mock_get.side_effect = [ARBOL, STATS, STATS]
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

    # --- S13: gestión de usuarios ---

    @patch("atenciones.views.api_get")
    def test_usuarios_lista(self, mock_get):
        self._como(JEFE)
        mock_get.return_value = [
            {"id": 1, "display_name": "Activo Uno", "role": "Tecnico", "activo": True},
            {
                "id": 11,
                "display_name": "Gabriel Torrico",
                "role": "Tecnico",
                "activo": False,
            },
        ]
        r = self.client.get("/usuarios/")
        self.assertEqual(r.status_code, 200)
        mock_get.assert_any_call(
            "/api/usuarios", "t", {"incluir_inactivos": "true"}
        )
        self.assertContains(r, "Activo Uno")
        self.assertContains(r, "Gabriel Torrico")
        self.assertContains(r, "inactivo")
        self.assertContains(r, "Reactivar")
        self.assertContains(r, "1 activos · 1 de baja")

    def test_usuarios_sin_permiso_redirige(self):
        self._como(TECNICO)
        self.assertRedirects(
            self.client.get("/usuarios/"),
            "/atenciones/",
            fetch_redirect_response=False,
        )

    @patch("atenciones.views.api_patch")
    def test_usuarios_desactivar(self, mock_patch):
        self._como(JEFE)
        r = self.client.post(
            "/usuarios/accion/", {"accion": "desactivar", "id": "11"}
        )
        self.assertRedirects(r, "/usuarios/", fetch_redirect_response=False)
        mock_patch.assert_called_once_with(
            "/api/usuarios/11/activo", "t", {"activo": False}
        )

    @patch("atenciones.views.api_post")
    def test_usuarios_crear(self, mock_post):
        self._como(JEFE)
        r = self.client.post(
            "/usuarios/accion/",
            {
                "accion": "crear",
                "email": "nuevo@upds.edu.bo",
                "nombre": "Nuevo Tecnico",
                "role": "Tecnico",
                "password": "",
            },
        )
        self.assertRedirects(r, "/usuarios/", fetch_redirect_response=False)
        mock_post.assert_called_once_with(
            "/api/usuarios",
            "t",
            {
                "email": "nuevo@upds.edu.bo",
                "display_name": "Nuevo Tecnico",
                "role": "Tecnico",
            },
        )

    @patch("atenciones.views.api_put")
    def test_jerarquia_mover_a_dependencia(self, mock_put):
        self._como(JEFE)
        r = self.client.post(
            "/jerarquia/accion/",
            {"accion": "mover", "tipo": "area", "id": "50", "destino": "g:4:3"},
        )
        self.assertRedirects(r, "/jerarquia/", fetch_redirect_response=False)
        mock_put.assert_called_once_with(
            "/api/jerarquia/areas/50", "t", {"grupo_padre_id": 3, "grupo_id": 4}
        )

    @patch("atenciones.views.api_put")
    def test_jerarquia_mover_a_sector_directo(self, mock_put):
        self._como(JEFE)
        r = self.client.post(
            "/jerarquia/accion/",
            {"accion": "mover", "tipo": "area", "id": "50", "destino": "s:3"},
        )
        self.assertRedirects(r, "/jerarquia/", fetch_redirect_response=False)
        mock_put.assert_called_once_with(
            "/api/jerarquia/areas/50", "t", {"grupo_padre_id": 3, "grupo_id": None}
        )

    @patch("atenciones.views.api_get")
    def test_lista_filtra_por_tecnico(self, mock_get):
        self._como(JEFE)
        mock_get.side_effect = lambda path, *a, **k: (
            [{"id": 11, "display_name": "Gabriel", "role": "Tecnico", "activo": False}]
            if path == "/api/usuarios"
            else [ATENCIONES[0]]
        )
        r = self.client.get("/atenciones/?tecnico=11")
        self.assertEqual(r.status_code, 200)
        llamadas = [
            c for c in mock_get.call_args_list if c[0][0] == "/api/atenciones"
        ]
        self.assertEqual(llamadas[0][0][2], {"usuario_id": "11"})


AVISO_SIN_VINCULO = (
    "Tu cuenta no está vinculada a la nómina; pedile al Jefe que la vincule"
)


def _api_lab(yo):
    """api_get de views_lab: /equipo/yo devuelve `yo` (o lanza), el resto vacío."""
    from atenciones.api import ApiError

    def _fake(path, *a, **k):
        if path == "/api/laboratorios/equipo/yo":
            if yo is None:
                raise ApiError(404, AVISO_SIN_VINCULO)
            return yo
        return []

    return _fake


class IdentidadAuxiliarTest(TestCase):
    def _como(self, usuario, **extra):
        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = usuario
        for k, v in extra.items():
            session[k] = v
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key

    @patch("atenciones.views_lab.api_get")
    @patch("atenciones.views.login_api")
    def test_login_guarda_nombre_vinculado(self, mock_login, mock_get):
        mock_login.return_value = {"token": "tok", "user": AUXILIAR}
        mock_get.side_effect = _api_lab(
            {"nombre": "Ana Pérez", "encargado": True, "activo": True}
        )
        r = self.client.post("/login/", {"email": "a@b.co", "password": "x"})
        self.assertRedirects(r, "/auxiliares/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["auxiliar_nombre"], "Ana Pérez")
        self.assertTrue(self.client.session["auxiliar_encargado"])
        mock_get.assert_any_call("/api/laboratorios/equipo/yo", "tok")

    @patch("atenciones.views_lab.api_get")
    @patch("atenciones.views.login_api")
    def test_login_tecnico_no_consulta_nomina(self, mock_login, mock_get):
        mock_login.return_value = {"token": "tok", "user": TECNICO}
        self.client.post("/login/", {"email": "a@b.co", "password": "x"})
        mock_get.assert_not_called()
        self.assertNotIn("auxiliar_nombre", self.client.session)

    @patch("atenciones.views_lab.api_get")
    @patch("atenciones.views.login_api")
    def test_login_sin_vinculo_muestra_aviso_sin_soy(self, mock_login, mock_get):
        mock_login.return_value = {"token": "tok", "user": AUXILIAR}
        mock_get.side_effect = _api_lab(None)
        self.client.post("/login/", {"email": "a@b.co", "password": "x"})
        self.assertNotIn("auxiliar_nombre", self.client.session)
        r = self.client.get("/auxiliares/novedades/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, AVISO_SIN_VINCULO)
        self.assertNotContains(r, "/auxiliares/soy/")

    @patch("atenciones.views_lab.requests.post")
    @patch("atenciones.views_lab.api_get")
    def test_sin_vinculo_no_publica_novedad(self, mock_get, mock_post):
        self._como(AUXILIAR)
        mock_get.side_effect = _api_lab(None)
        r = self.client.post(
            "/auxiliares/novedades/", {"action": "crear", "texto": "hola"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, AVISO_SIN_VINCULO)
        mock_post.assert_not_called()

    @patch("atenciones.views_lab.api_get")
    def test_sin_vinculo_lab_nueva_avisa_sin_redirigir(self, mock_get):
        self._como(AUXILIAR)
        mock_get.side_effect = _api_lab(None)
        r = self.client.get("/auxiliares/atenciones/nueva/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, AVISO_SIN_VINCULO)

    def test_soy_ya_no_existe(self):
        self._como(AUXILIAR, auxiliar_nombre="Ana Pérez")
        self.assertEqual(self.client.get("/auxiliares/soy/").status_code, 404)

    @patch("atenciones.views_lab.api_get")
    def test_navbar_muestra_nombre_sin_cambiar(self, mock_get):
        self._como(AUXILIAR, auxiliar_nombre="Ana Pérez")
        mock_get.side_effect = _api_lab(None)
        r = self.client.get("/auxiliares/novedades/")
        self.assertContains(r, "Ana Pérez")
        self.assertNotContains(r, ">cambiar</a>")
        self.assertNotContains(r, AVISO_SIN_VINCULO)

    def test_quien_reporta_usa_nombre_vinculado(self):
        from django.test import RequestFactory

        from atenciones.views_lab import _quien_reporta

        req = RequestFactory().get("/")
        req.session = {"usuario": AUXILIAR, "auxiliar_nombre": "Ana Pérez"}
        self.assertEqual(_quien_reporta(req), "Ana Pérez")
        req.session = {"usuario": AUXILIAR}
        self.assertEqual(_quien_reporta(req), "")
        req.session = {"usuario": TECNICO}
        self.assertEqual(_quien_reporta(req), "Diego")

    @patch("atenciones.views_lab.requests.post")
    @patch("atenciones.views_lab.api_get")
    def test_novedad_se_publica_con_nombre_vinculado(self, mock_get, mock_post):
        self._como(AUXILIAR, auxiliar_nombre="Ana Pérez")
        mock_get.side_effect = _api_lab(None)
        mock_post.return_value.status_code = 201
        self.client.post(
            "/auxiliares/novedades/",
            {"action": "crear", "texto": "hola", "auxiliar_nombre": "Otro"},
        )
        self.assertEqual(mock_post.call_args.kwargs["data"]["auxiliar_nombre"], "Ana Pérez")

    @patch("atenciones.views_lab.api_post")
    @patch("atenciones.views_lab.api_get")
    def test_lab_nueva_auxiliar_principal_fijo(self, mock_get, mock_post):
        self._como(AUXILIAR, auxiliar_nombre="Ana Pérez")
        mock_get.side_effect = _api_lab(None)
        r = self.client.get("/auxiliares/atenciones/nueva/")
        self.assertContains(r, 'value="Ana Pérez" readonly')
        self.client.post(
            "/auxiliares/atenciones/nueva/",
            {
                "action": "enviar",
                "laboratorio_id": "3",
                "categoria": "Hardware",
                "descripcion": "d",
                "solucion": "s",
                "auxiliar_nombre": "Otro",
                "auxiliar_extra": "Beto",
            },
        )
        payload = mock_post.call_args[0][2]
        self.assertEqual(payload["auxiliar_nombre"], "Ana Pérez + Beto")


EQUIPO_NOMINA = {
    "auxiliares": [
        {"nombre": "Ana Rojas", "activo": True, "encargado": False, "usuario_id": 21},
        {"nombre": "Luis Paz", "activo": True, "encargado": False, "usuario_id": None},
        {"nombre": "Baja Vieja", "activo": False, "encargado": False, "usuario_id": None},
    ]
}
USUARIOS_AUX = [
    {"id": 21, "display_name": "Cuenta Ana", "role": "Auxiliar", "activo": True},
    {"id": 22, "display_name": "Cuenta Nueva", "role": "Encargado", "activo": True},
    {"id": 2, "display_name": "Diego", "role": "Tecnico", "activo": True},
]
URL_VINCULAR = "/api/laboratorios/equipo/vincular"


def _fake_usuarios(path, *a, **k):
    if path == "/api/laboratorios/equipo":
        return EQUIPO_NOMINA
    if path == "/api/usuarios":
        return USUARIOS_AUX
    return []


class VinculoNominaTest(TestCase):
    def _como(self, usuario):
        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = usuario
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key

    def _flash(self):
        return self.client.session.get("flash")

    @patch("atenciones.views.api_get", side_effect=_fake_usuarios)
    def test_lista_muestra_vinculado_y_sin_vincular(self, _get):
        self._como(JEFE)
        r = self.client.get("/usuarios/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Nómina: <strong>Ana Rojas</strong>", html=False)
        self.assertContains(r, "Sin vincular")
        self.assertContains(r, 'value="vincular"')
        self.assertContains(r, 'value="desvincular"')
        # Solo miembros activos en el selector; el ya vinculado se marca.
        self.assertContains(r, "Luis Paz")
        self.assertContains(r, "Ana Rojas (vinculado)")
        self.assertNotContains(r, "Baja Vieja")

    @patch("atenciones.views.api_get", side_effect=_fake_usuarios)
    def test_no_jefe_no_ve_controles_de_vinculo(self, _get):
        self._como(MATTIAS)
        r = self.client.get("/usuarios/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'value="vincular"')
        self.assertNotContains(r, 'value="desvincular"')

    @patch("atenciones.views.api_post")
    def test_vincular_envia_payload(self, mock_post):
        self._como(JEFE)
        r = self.client.post(
            "/usuarios/accion/",
            {"accion": "vincular", "id": "22", "nombre": "Luis Paz"},
        )
        self.assertRedirects(r, "/usuarios/", fetch_redirect_response=False)
        mock_post.assert_called_once_with(
            URL_VINCULAR, "t", {"nombre": "Luis Paz", "usuario_id": 22}
        )
        self.assertEqual(self._flash()["tipo"], "ok")

    @patch("atenciones.views.api_post")
    def test_desvincular_envia_usuario_id_null(self, mock_post):
        self._como(JEFE)
        self.client.post(
            "/usuarios/accion/",
            {"accion": "desvincular", "id": "21", "nombre": "Ana Rojas"},
        )
        mock_post.assert_called_once_with(
            URL_VINCULAR, "t", {"nombre": "Ana Rojas", "usuario_id": None}
        )

    @patch("atenciones.views.api_post")
    def test_vincular_error_api_se_muestra(self, mock_post):
        from atenciones.api import ApiError

        mock_post.side_effect = ApiError(400, "El usuario está desactivado")
        self._como(JEFE)
        self.client.post(
            "/usuarios/accion/",
            {"accion": "vincular", "id": "22", "nombre": "Luis Paz"},
        )
        self.assertEqual(
            self._flash(), {"tipo": "error", "texto": "El usuario está desactivado"}
        )

    @patch("atenciones.views.api_post")
    def test_no_jefe_no_puede_vincular(self, mock_post):
        self._como(MATTIAS)
        self.client.post(
            "/usuarios/accion/",
            {"accion": "vincular", "id": "22", "nombre": "Luis Paz"},
        )
        mock_post.assert_not_called()
        self.assertEqual(self._flash()["tipo"], "error")

    @patch("atenciones.views.api_post")
    def test_crear_con_miembro_de_nomina_vincula_nuevo_id(self, mock_post):
        mock_post.side_effect = lambda path, *a, **k: (
            {"id": 30, "display_name": "Luis"} if path == "/api/usuarios" else {}
        )
        self._como(JEFE)
        self.client.post(
            "/usuarios/accion/",
            {
                "accion": "crear",
                "email": "luis@upds.edu.bo",
                "nombre": "Luis",
                "role": "Auxiliar",
                "password": "",
                "nomina": "Luis Paz",
            },
        )
        self.assertEqual(mock_post.call_count, 2)
        mock_post.assert_called_with(
            URL_VINCULAR, "t", {"nombre": "Luis Paz", "usuario_id": 30}
        )
        self.assertEqual(self._flash()["tipo"], "ok")

    @patch("atenciones.views.api_post")
    def test_crear_si_falla_vinculo_usuario_queda_creado(self, mock_post):
        from atenciones.api import ApiError

        def _fake(path, *a, **k):
            if path == "/api/usuarios":
                return {"id": 30}
            raise ApiError(404, "Auxiliar 'Luis Paz' no existe")

        mock_post.side_effect = _fake
        self._como(JEFE)
        self.client.post(
            "/usuarios/accion/",
            {
                "accion": "crear",
                "email": "luis@upds.edu.bo",
                "nombre": "Luis",
                "role": "Auxiliar",
                "nomina": "Luis Paz",
            },
        )
        flash = self._flash()
        self.assertEqual(flash["tipo"], "error")
        self.assertIn("Usuario creado", flash["texto"])
        self.assertIn("Auxiliar 'Luis Paz' no existe", flash["texto"])

    @patch("atenciones.views.api_post")
    def test_crear_tecnico_ignora_nomina(self, mock_post):
        mock_post.return_value = {"id": 31}
        self._como(JEFE)
        self.client.post(
            "/usuarios/accion/",
            {
                "accion": "crear",
                "email": "t@upds.edu.bo",
                "nombre": "T",
                "role": "Tecnico",
                "nomina": "Luis Paz",
            },
        )
        mock_post.assert_called_once()


ENCARGADO = {
    "id": 11,
    "display_name": "Encargado Labs",
    "role": "Encargado",
    "can_view_dashboard": False,
}
AUX_EMAIL = {**AUXILIAR, "email": "aux@upds.edu.bo"}


class PerfilAuxiliarTest(TestCase):
    def _como(self, usuario, **extra):
        session = self.client.session
        session["jwt"] = "t"
        session["usuario"] = usuario
        for k, v in extra.items():
            session[k] = v
        session.save()
        self.client.cookies[_settings.SESSION_COOKIE_NAME] = session.session_key

    def _flash(self):
        return self.client.session.get("flash")

    def _password(self, url, nueva="nueva1234", repetir=None):
        return self.client.post(
            url,
            {
                "accion": "password",
                "actual": "vieja1234",
                "nueva": nueva,
                "repetir": nueva if repetir is None else repetir,
            },
        )

    def test_auxiliar_ve_sus_datos_y_nombre_vinculado(self):
        self._como(AUX_EMAIL, auxiliar_nombre="Ana Pérez")
        r = self.client.get("/auxiliares/perfil/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Auxiliar Soporte")
        self.assertContains(r, "aux@upds.edu.bo")
        self.assertContains(r, "Ana Pérez")
        self.assertContains(r, 'name="repetir"')
        self.assertContains(r, 'action="/auxiliares/perfil/guardar/"')
        self.assertNotContains(r, 'value="especialidad"')

    @patch("atenciones.views_lab.api_get")
    def test_sin_vinculo_muestra_aviso(self, mock_get):
        self._como(AUX_EMAIL)
        mock_get.side_effect = _api_lab(None)
        r = self.client.get("/auxiliares/perfil/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sin vincular")
        self.assertContains(r, AVISO_SIN_VINCULO)

    @patch("atenciones.views_lab.api_get")
    @patch("atenciones.views.login_api")
    @patch("atenciones.views.api_post")
    def test_cambiar_password_ok(self, mock_post, mock_login, mock_get):
        self._como(AUX_EMAIL, auxiliar_nombre="Ana Pérez")
        mock_login.return_value = {"token": "tok2", "user": AUX_EMAIL}
        mock_get.side_effect = _api_lab(
            {"nombre": "Ana Pérez", "encargado": False, "activo": True}
        )
        r = self._password("/auxiliares/perfil/guardar/")
        self.assertRedirects(
            r, "/auxiliares/perfil/", fetch_redirect_response=False
        )
        mock_post.assert_called_once_with(
            "/api/auth/password", "t", {"actual": "vieja1234", "nueva": "nueva1234"}
        )
        mock_login.assert_called_once_with("aux@upds.edu.bo", "nueva1234")
        self.assertEqual(self.client.session["jwt"], "tok2")
        self.assertEqual(self.client.session["auxiliar_nombre"], "Ana Pérez")
        self.assertEqual(self._flash(), {"tipo": "ok", "texto": "Contraseña cambiada."})

    @patch("atenciones.views.api_post")
    def test_repetir_distinto_no_llama_api(self, mock_post):
        self._como(AUX_EMAIL, auxiliar_nombre="Ana Pérez")
        r = self._password("/auxiliares/perfil/guardar/", repetir="otra12345")
        self.assertRedirects(
            r, "/auxiliares/perfil/", fetch_redirect_response=False
        )
        mock_post.assert_not_called()
        self.assertEqual(self._flash()["tipo"], "error")
        self.assertIn("no coinciden", self._flash()["texto"])

    @patch("atenciones.views.login_api")
    @patch("atenciones.views.api_post")
    def test_error_de_api_se_muestra(self, mock_post, mock_login):
        from atenciones.api import ApiError

        self._como(AUX_EMAIL, auxiliar_nombre="Ana Pérez")
        mock_post.side_effect = ApiError(400, "La contraseña actual no es correcta")
        r = self._password("/auxiliares/perfil/guardar/")
        self.assertRedirects(
            r, "/auxiliares/perfil/", fetch_redirect_response=False
        )
        mock_login.assert_not_called()
        self.assertEqual(
            self._flash(),
            {"tipo": "error", "texto": "La contraseña actual no es correcta"},
        )

    def test_tecnico_va_a_su_perfil(self):
        self._como(TECNICO)
        self.assertRedirects(
            self.client.get("/auxiliares/perfil/"),
            "/perfil/",
            fetch_redirect_response=False,
        )

    @patch("atenciones.views.api_post")
    def test_tecnico_no_usa_guardar_de_auxiliares(self, mock_post):
        self._como(TECNICO)
        r = self._password("/auxiliares/perfil/guardar/")
        self.assertRedirects(r, "/perfil/", fetch_redirect_response=False)
        mock_post.assert_not_called()

    def test_perfil_de_soporte_redirige_a_auxiliar_y_encargado(self):
        for usuario in (AUXILIAR, ENCARGADO):
            self._como(usuario, auxiliar_nombre="Ana Pérez")
            self.assertRedirects(
                self.client.get("/perfil/"),
                "/auxiliares/perfil/",
                fetch_redirect_response=False,
            )

    @patch("atenciones.views.login_api")
    @patch("atenciones.views.api_post")
    def test_perfil_de_soporte_sigue_cambiando_password(self, mock_post, mock_login):
        tecnico = {**TECNICO, "email": "d@upds.edu.bo"}
        self._como(tecnico)
        mock_login.return_value = {"token": "tok3", "user": tecnico}
        r = self._password("/perfil/guardar/")
        self.assertRedirects(r, "/perfil/", fetch_redirect_response=False)
        mock_post.assert_called_once_with(
            "/api/auth/password", "t", {"actual": "vieja1234", "nueva": "nueva1234"}
        )
        mock_login.assert_called_once_with("d@upds.edu.bo", "nueva1234")
        self.assertEqual(self.client.session["jwt"], "tok3")
        self.assertEqual(self._flash(), {"tipo": "ok", "texto": "Contraseña cambiada."})

    def test_navbar_perfil_en_panel_auxiliares(self):
        for usuario in (AUXILIAR, ENCARGADO):
            self._como(usuario, auxiliar_nombre="Ana Pérez")
            r = self.client.get("/auxiliares/perfil/")
            self.assertEqual(r.status_code, 200)
            self.assertContains(
                r, '<div class="sistema-panel" data-sistema-panel="AUXILIARES">'
            )
            self.assertContains(r, 'data-sistema-panel="SOPORTE" hidden')
            self.assertContains(
                r,
                '<a class="side-link active" href="/auxiliares/perfil/"',
            )
