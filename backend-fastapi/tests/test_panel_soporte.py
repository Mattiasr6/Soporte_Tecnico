"""M8: Soporte dashboard and monthly report computed in the API.

The Django views (`dashboard_vista`, `reportes_vista`) built their KPIs and
chart series from GET /api/atenciones/stats in Python (`_graficos`, `_ficha`,
`_kpis_reporte`...). Those helpers now live in `app.services.panel_soporte`
and are served by /api/atenciones/dashboard and /api/atenciones/reporte, so the
Angular screens stay thin. Same permission as Django `_puede_dashboard`:
Jefe or `CanViewDashboard`; anyone else gets 403.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.db.base import SessionLocal
from app.main import app
from app.models.atencion import Atencion
from app.models.usuario import Usuario
from app.services import panel_soporte as ps
from app.services.tokens import crear_token

client = TestClient(app)
DOMAIN = "test-panel-soporte.local"
MARK = "TEST-M8-"


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
        usuario.token_version,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_usuario() -> Iterator[Callable[..., Usuario]]:
    created: list[int] = []

    def _make(role: str, dashboard: bool = False) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"Prueba {role}",
                role=role,
                activo=True,
                can_view_dashboard=dashboard,
                created_at=now,
                updated_at=now,
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
            db.expunge(usuario)
        created.append(usuario.id)
        return usuario

    yield _make

    with SessionLocal() as db:
        for uid in created:
            db.execute(delete(Atencion).where(Atencion.usuario_id == uid))
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


def _atencion(
    usuario_id: int,
    fecha: date,
    categoria: str,
    *,
    area: str = "Area M8",
    medio: str = "Interno",
    tipo: str = "ADM",
    fuera: bool = False,
    solucion: str = "ok",
) -> Atencion:
    return Atencion(
        usuario_id=usuario_id,
        area_solicitante=area,
        medio_solicitud=medio,
        usuario_solicitante=tipo,
        categoria=categoria,
        descripcion=f"{MARK}{categoria}",
        solucion=solucion,
        fuera_de_turno=fuera,
        fecha_registro=fecha,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def datos_2001(make_usuario: Callable[..., Usuario]) -> Usuario:
    """A Jefe with attentions in 2001 only (no other data lives that far back).

    2001-02: 2 rows (1 fuera de turno). 2001-03: 5 rows, 2 fuera de turno,
    categories Hardware x3, Software x2, areas A x3 / B x2.
    """
    jefe = make_usuario("Jefe")
    filas = [
        _atencion(jefe.id, date(2001, 2, 5), "Hardware", fuera=True),
        _atencion(jefe.id, date(2001, 2, 6), "Redes"),
        _atencion(jefe.id, date(2001, 3, 1), "Hardware", area="A", solucion="corta"),
        _atencion(
            jefe.id, date(2001, 3, 2), "Hardware", area="A", solucion="la mas larga"
        ),
        _atencion(jefe.id, date(2001, 3, 3), "Hardware", area="A", fuera=True),
        _atencion(
            jefe.id,
            date(2001, 3, 5),
            "Software",
            area="B",
            medio="WhatsApp",
            fuera=True,
        ),
        _atencion(jefe.id, date(2001, 3, 6), "Software", area="B", tipo="DOC"),
    ]
    with SessionLocal() as db:
        db.add_all(filas)
        db.commit()
    return jefe


# ---------------------------------------------------------------- pure helpers


def test_dias_habiles_cuenta_lunes_a_sabado():
    # March 2001: 31 days, 4 Sundays (4, 11, 18, 25)
    assert ps.dias_habiles(2001, 3) == 27
    # Whole 2001: 365 days, 52 Sundays
    assert ps.dias_habiles(2001, None) == 313


def test_periodo_reporte_valida_mes_y_vista():
    hoy = date(2026, 10, 10)
    p = ps.periodo_reporte("2001-03", "mes", hoy)
    assert p == {
        "vista": "mes",
        "mes": "2001-03",
        "anio": 2001,
        "mes_num": 3,
        "etiqueta": "Marzo 2001",
        "es_mes_en_curso": False,
    }
    anio = ps.periodo_reporte("2001-03", "anio", hoy)
    assert anio["etiqueta"] == "Acumulado enero\u2013marzo 2001"
    # Invalid month or view fall back to the current month / "mes"
    actual = ps.periodo_reporte("2001-13", "semana", hoy)
    assert actual["mes"] == "2026-10"
    assert actual["vista"] == "mes"
    assert actual["etiqueta"] == "Octubre 2026 (parcial)"
    assert actual["es_mes_en_curso"] is True


def test_kpis_reporte_como_django():
    s_mes = {"total": 5, "fuera_de_turno": 2, "por_area": [{}, {}]}
    s_prev = {"total": 2, "fuera_de_turno": 1}
    s_evol = {"por_mes": [{"total": 2}, {"total": 5}, {"total": 0}]}
    k = ps.kpis_reporte(s_mes, s_prev, s_evol, 27)
    assert k == {
        "total": 5,
        "prev_total": 2,
        "delta_abs": 3,
        "delta_pct": 150.0,
        "fuera_pct": 40.0,
        "fuera_delta_pts": -10.0,
        "promedio_dia": 0.2,
        "dias_periodo": 27,
        "areas_distintas": 2,
        "meses_activos": 2,
    }
    # Previous month without rows: no percentage delta
    vacio = ps.kpis_reporte(s_mes, {"total": 0, "fuera_de_turno": 0}, s_evol, 27)
    assert vacio["delta_abs"] == 5
    assert vacio["delta_pct"] is None
    assert vacio["fuera_delta_pts"] is None


def test_evolucion_rellena_meses_sin_datos():
    stats = {
        "por_mes": [
            {"anio": 2001, "mes": 1, "total": 4},
            {"anio": 2001, "mes": 3, "total": 2},
            {"anio": 2000, "mes": 2, "total": 9},
        ]
    }
    assert ps.evolucion(stats, 2001, 3) == {
        "labels": ["ene", "feb", "mar"],
        "values": [4, 0, 2],
    }


def test_top_areas_ordena_y_calcula_porcentaje():
    stats = {
        "por_area": [
            {"area": "B", "total": 1},
            {"area": "A", "total": 3},
            {"area": "C", "total": 1},
        ]
    }
    assert ps.top_areas(stats, 5) == [
        {"area": "A", "total": 3, "pct": 60.0},
        {"area": "B", "total": 1, "pct": 20.0},
        {"area": "C", "total": 1, "pct": 20.0},
    ]


def test_destacados_elige_la_solucion_mas_larga_por_categoria():
    filas = [
        {"id": 3, "categoria": "Hardware", "solucion": "abc", "area_solicitante": "A"},
        {"id": 2, "categoria": "Hardware", "solucion": "abcd", "area_solicitante": "A"},
        {"id": 1, "categoria": "Hardware", "solucion": "wxyz", "area_solicitante": "B"},
        {"id": 9, "categoria": "Software", "solucion": "s", "area_solicitante": "C"},
    ]
    salida = ps.destacados(filas, ["Hardware", "Redes", "Software"])
    # Same length -> lowest id wins (Django key: (len, -id))
    assert [d["id"] for d in salida] == [1, 9]
    assert salida[0]["area"] == "B"


# ---------------------------------------------------------------- /reporte


def test_reporte_niega_a_quien_no_ve_dashboard(make_usuario):
    tecnico = make_usuario("Tecnico")
    r = client.get("/api/atenciones/reporte", headers=_auth(tecnico))
    assert r.status_code == 403


def test_reporte_permite_flag_dashboard(make_usuario):
    tecnico = make_usuario("Tecnico", dashboard=True)
    r = client.get(
        "/api/atenciones/reporte", params={"mes": "2001-03"}, headers=_auth(tecnico)
    )
    assert r.status_code == 200, r.text


def test_reporte_mes(datos_2001):
    r = client.get(
        "/api/atenciones/reporte",
        params={"mes": "2001-03", "vista": "mes"},
        headers=_auth(datos_2001),
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert set(p) == {"periodo", "kpis", "charts", "destacados", "metodologia"}
    assert p["periodo"]["etiqueta"] == "Marzo 2001"
    k = p["kpis"]
    assert k["total"] == 5
    assert k["prev_total"] == 2
    assert k["delta_abs"] == 3
    assert k["delta_pct"] == 150.0
    assert k["fuera_pct"] == 40.0
    assert k["fuera_delta_pts"] == -10.0
    assert k["dias_periodo"] == 27
    assert k["promedio_dia"] == 0.2
    assert k["areas_distintas"] == 2
    assert k["meses_activos"] == 2
    c = p["charts"]
    assert c["evolucion"] == {"labels": ["ene", "feb", "mar"], "values": [0, 2, 5]}
    assert c["categoria"] == {"labels": ["Hardware", "Software"], "values": [3, 2]}
    assert c["medio"] == {"labels": ["Interno", "WhatsApp"], "values": [4, 1]}
    assert c["tipo_solicitante"] == {"labels": ["ADM", "DOC"], "values": [4, 1]}
    assert c["top_areas"][0] == {"area": "A", "total": 3, "pct": 60.0}
    # Featured work: top 3 categories of the month, longest solution each
    assert [d["categoria"] for d in p["destacados"]] == ["Hardware", "Software"]
    assert p["destacados"][0]["solucion"] == "la mas larga"
    assert p["metodologia"]["periodo"] == "01/03/2001\u201331/03/2001"
    assert p["metodologia"]["corte"] == "Mes cerrado"


def test_reporte_anio_acumulado(datos_2001):
    r = client.get(
        "/api/atenciones/reporte",
        params={"mes": "2001-03", "vista": "anio"},
        headers=_auth(datos_2001),
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["periodo"]["vista"] == "anio"
    assert p["kpis"]["total"] == 7
    assert p["kpis"]["prev_total"] is None
    assert p["kpis"]["dias_periodo"] == 313
    assert p["kpis"]["meses_activos"] == 2
    assert p["destacados"] == []
    assert p["metodologia"]["periodo"] == "01/01/2001\u201331/03/2001"
