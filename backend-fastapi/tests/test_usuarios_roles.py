"""T8: Soporte roles Decano and Invitado (6 roles in total).

Self-contained: the test DB has no seed users, so every test builds the
Usuarios rows it needs and the fixture deletes them (and any perfil) at teardown.
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
from app.routers.usuarios import ROLES_VALIDOS
from app.services.asignacion_perfiles import map_role
from app.services.tokens import crear_token

client = TestClient(app)
DOMAIN = "test-roles.local"
NEW_ROLES = ["Decano", "Invitado"]


@pytest.fixture
def make_usuario() -> Iterator[Callable[..., Usuario]]:
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
        # Users created through the API are also under DOMAIN.
        ids = list(created) + list(
            db.execute(
                text('select "Id" from "Usuarios" where "Email" like :d'),
                {"d": f"%@{DOMAIN}"},
            ).scalars()
        )
        for uid in set(ids):
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


def test_soporte_has_six_roles() -> None:
    assert set(ROLES_VALIDOS) == {
        "Tecnico",
        "Jefe",
        "Auxiliar",
        "Encargado",
        "Decano",
        "Invitado",
    }


@pytest.mark.parametrize("role", NEW_ROLES)
def test_jefe_creates_user_with_new_role(make_usuario, role: str) -> None:
    jefe = make_usuario("Jefe")
    r = client.post(
        "/api/usuarios",
        json={
            "email": f"nuevo-{role.lower()}@{DOMAIN}",
            "display_name": "X",
            "role": role,
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 201, r.text
    assert r.json()["role"] == role


@pytest.mark.parametrize("role", NEW_ROLES)
def test_jefe_changes_role_to_new_role(make_usuario, role: str) -> None:
    jefe = make_usuario("Jefe")
    target = make_usuario("Tecnico")
    r = client.patch(
        f"/api/usuarios/{target.id}/rol", json={"role": role}, headers=_auth(jefe)
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == role


@pytest.mark.parametrize("role", NEW_ROLES)
def test_new_roles_have_no_user_management(make_usuario, role: str) -> None:
    """Their Soporte permissions are not defined yet: they get no privileges."""
    actor = make_usuario(role)
    target = make_usuario("Tecnico")
    r = client.post(
        "/api/usuarios",
        json={
            "email": f"nope-{role.lower()}@{DOMAIN}",
            "display_name": "X",
            "role": "Tecnico",
        },
        headers=_auth(actor),
    )
    assert r.status_code == 403, r.text
    r = client.patch(
        f"/api/usuarios/{target.id}/rol", json={"role": "Jefe"}, headers=_auth(actor)
    )
    assert r.status_code == 403, r.text


@pytest.mark.parametrize("role", NEW_ROLES)
def test_new_roles_are_not_listed_as_technicians(make_usuario, role: str) -> None:
    usuario = make_usuario(role)
    r = client.get("/api/usuarios", headers=_auth(usuario))
    assert r.status_code == 200, r.text
    assert usuario.id not in {u["id"] for u in r.json()}


def test_invalid_role_message_lists_six_roles(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    r = client.post(
        "/api/usuarios",
        json={"email": f"malo@{DOMAIN}", "display_name": "X", "role": "Supervisor"},
        headers=_auth(jefe),
    )
    assert r.status_code == 400, r.text
    assert "Decano" in r.text and "Invitado" in r.text


@pytest.mark.parametrize(
    ("role", "rol"),
    [("Decano", "decano"), ("Invitado", "invitado"), ("Tecnico", "tecnico")],
)
def test_new_roles_map_to_asignacion_rol(role: str, rol: str) -> None:
    assert map_role(role) == rol
