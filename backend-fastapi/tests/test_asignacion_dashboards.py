"""T7: dashboards of the asignacion module (old Supabase RPCs fn_dashboard_*).

The four SQL functions (operacion, uso, detalle, fallas) only allow
fn_puede_gestionar_auxiliares (admin or encargado; the Angular route uses the
same guard). The API checks it first so a missing permission is a 403, and it
validates the date range (hasta >= desde, at most 400 days) as a 422 before
calling the function. The JSON the functions build is returned unchanged.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario
from app.services.tokens import crear_token

client = TestClient(app)
API = "/api/asignacion/dashboard"
DOMAIN = "test-asignacion-dash.local"
PREFIX = "ZZDA-"
RANGO = {"desde": "2026-01-01", "hasta": "2026-01-31"}

KEYS = {
    "operacion": {"kpis", "por_dia", "por_tipo", "por_lab", "auxiliares", "pcs"},
    "uso": {"totales", "materias", "eventos", "por_lab", "actividades_lab"},
    "detalle": {"uso_por_dia", "carreras", "docentes", "tickets_por_turno"},
    "fallas": {"total", "con_ficha", "fallas", "por_categoria", "resultados"},
}


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_usuario() -> Iterator[Callable[[str], Usuario]]:
    created: list[int] = []

    def _make(role: str) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"Prueba {role}",
                role=role,
                activo=True,
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
        labs = "select id from horarios.ambientes where codigo like :p"
        params = {"p": f"{PREFIX}%"}
        db.execute(
            text(f"delete from horarios.atenciones where ambiente_id in ({labs})"),
            params,
        )
        db.execute(text("delete from horarios.ambientes where codigo like :p"), params)
        for uid in created:
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


@pytest.fixture
def lab_con_ticket() -> int:
    """A test laboratory with one ticket inside RANGO (cleaned by make_usuario)."""
    with SessionLocal() as db:
        lab_id = db.execute(
            text(
                "insert into horarios.ambientes (codigo, nombre)"
                " values (:c, 'Lab de prueba') returning id"
            ),
            {"c": f"{PREFIX}{uuid4().hex[:6]}"},
        ).scalar_one()
        db.execute(
            text(
                "insert into horarios.atenciones (ambiente_id, descripcion, creado_en)"
                " values (:a, 'Prueba dashboard', timestamptz '2026-01-15 10:00:00-04')"
            ),
            {"a": lab_id},
        )
        db.commit()
    return lab_id


@pytest.mark.parametrize("nombre", sorted(KEYS))
def test_jefe_and_encargado_get_dashboard(
    nombre: str, make_usuario, lab_con_ticket: int
) -> None:
    for role in ("Jefe", "Encargado"):
        r = client.get(
            f"{API}/{nombre}", params=RANGO, headers=_auth(make_usuario(role))
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, dict)
        assert KEYS[nombre] <= body.keys()


def test_operacion_counts_seeded_ticket(make_usuario, lab_con_ticket: int) -> None:
    r = client.get(
        f"{API}/operacion", params=RANGO, headers=_auth(make_usuario("Jefe"))
    )
    assert r.status_code == 200, r.text
    labs = {lab["id"]: lab for lab in r.json()["por_lab"]}
    assert labs[lab_con_ticket]["tickets"] == 1


@pytest.mark.parametrize("nombre", sorted(KEYS))
@pytest.mark.parametrize("role", ["Auxiliar", "Tecnico"])
def test_without_permission_is_403(nombre: str, role: str, make_usuario) -> None:
    r = client.get(f"{API}/{nombre}", params=RANGO, headers=_auth(make_usuario(role)))
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "42501"


@pytest.mark.parametrize("nombre", sorted(KEYS))
@pytest.mark.parametrize(
    "params",
    [
        {"desde": "no-es-fecha", "hasta": "2026-01-31"},
        {"desde": "2026-01-01"},
        {"desde": "2026-02-01", "hasta": "2026-01-31"},
        {"desde": "2025-01-01", "hasta": "2026-06-30"},
    ],
)
def test_invalid_range_is_422(nombre: str, params: dict, make_usuario) -> None:
    r = client.get(
        f"{API}/{nombre}", params=params, headers=_auth(make_usuario("Jefe"))
    )
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("nombre", sorted(KEYS))
def test_without_token_is_401(nombre: str) -> None:
    assert client.get(f"{API}/{nombre}", params=RANGO).status_code == 401


def test_sql_range_rejection_is_422(make_usuario) -> None:
    # fn_dashboard_operacion counts the range inclusively (401 days > 400): the
    # API accepts the range but the function's own rejection is still a 422.
    params = {"desde": "2025-01-01", "hasta": "2026-02-05"}
    r = client.get(
        f"{API}/operacion", params=params, headers=_auth(make_usuario("Jefe"))
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "P0001"
