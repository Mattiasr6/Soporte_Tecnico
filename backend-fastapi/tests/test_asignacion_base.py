"""T2: API base for the asignacion module (ex ASIGNACION_DE-HORARIOS).

Users and perfiles created here are deleted at teardown. The test DB has no
seed data, so every test builds the Usuarios rows it needs.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import Settings
from app.db.asignacion import bind_usuario_context
from app.db.base import SessionLocal
from app.main import app, configure_cors
from app.models.usuario import Usuario
from app.services.asignacion_perfiles import ensure_perfil, map_role
from app.services.tokens import crear_token

client = TestClient(app)
DOMAIN = "test-asignacion.local"
ME = "/api/asignacion/me"


@pytest.fixture
def make_usuario() -> Iterator[Callable[..., Usuario]]:
    created: list[int] = []

    def _make(role: str, activo: bool = True) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"Prueba {role}",
                role=role,
                activo=activo,
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


def _set_role(usuario_id: int, role: str) -> None:
    with SessionLocal() as db:
        db.execute(
            text('update "Usuarios" set "Role" = :role where "Id" = :uid'),
            {"role": role, "uid": usuario_id},
        )
        db.commit()


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Jefe", "admin"),
        ("Encargado", "encargado"),
        ("Auxiliar", "auxiliar"),
        ("Tecnico", "invitado"),
    ],
)
def test_role_mapping(role: str, expected: str) -> None:
    assert map_role(role) == expected


def test_unknown_role_gets_least_privilege() -> None:
    assert map_role("Otro") == "invitado"


def test_me_without_token_is_401() -> None:
    assert client.get(ME).status_code == 401


def test_me_creates_admin_perfil_bound_to_db_context(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    r = client.get(ME, headers=_auth(jefe))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "usuario_id",
        "perfil_id",
        "nombre_completo",
        "correo",
        "rol",
        "activo",
        "turno_habitual",
        "sabado_rotativo",
    }
    assert body["usuario_id"] == jefe.id
    assert body["rol"] == "admin"
    assert body["activo"] is True
    assert body["correo"] == jefe.email
    assert body["nombre_completo"] == jefe.display_name

    with SessionLocal() as db:
        db.execute(
            text("select set_config('app.usuario_id', :uid, true)"),
            {"uid": str(jefe.id)},
        )
        current = db.execute(text("select horarios.fn_usuario_actual()")).scalar()
    assert str(current) == body["perfil_id"]


def test_role_change_in_usuarios_resyncs_perfil(make_usuario) -> None:
    usuario = make_usuario("Encargado")
    assert client.get(ME, headers=_auth(usuario)).json()["rol"] == "encargado"
    _set_role(usuario.id, "Auxiliar")
    assert client.get(ME, headers=_auth(usuario)).json()["rol"] == "auxiliar"


def test_demoted_jefe_resyncs_despite_admin_protection_trigger(make_usuario) -> None:
    """Usuarios is the source of truth: the self-demotion guard must not block it."""
    jefe = make_usuario("Jefe")
    first = client.get(ME, headers=_auth(jefe)).json()
    _set_role(jefe.id, "Tecnico")
    r = client.get(ME, headers=_auth(jefe))
    assert r.status_code == 200, r.text
    assert r.json()["rol"] == "invitado"
    assert r.json()["perfil_id"] == first["perfil_id"]


def test_inactive_usuario_gets_inactive_perfil(make_usuario) -> None:
    usuario = make_usuario("Auxiliar", activo=False)
    with SessionLocal() as db:
        perfil_id = ensure_perfil(db, usuario)
        db.commit()
        row = db.execute(
            text("select rol, activo from horarios.perfiles where id = :id"),
            {"id": perfil_id},
        ).one()
    assert (row.rol, row.activo) == ("auxiliar", False)


def test_usuario_context_survives_commit(make_usuario) -> None:
    usuario = make_usuario("Encargado")
    with SessionLocal() as db:
        perfil_id = ensure_perfil(db, usuario)
        db.commit()
        bind_usuario_context(db, usuario.id)
        assert db.execute(text("select horarios.fn_usuario_actual()")).scalar() == (
            perfil_id
        )
        db.commit()
        assert db.execute(text("select horarios.fn_usuario_actual()")).scalar() == (
            perfil_id
        )
        assert db.execute(text("select horarios.fn_rol_actual()")).scalar() == (
            "encargado"
        )


def test_cors_origins_setting_is_comma_separated() -> None:
    settings = Settings(CORS_ORIGINS=" http://localhost:4200 ,http://127.0.0.1:4200,")
    assert settings.cors_origin_list == [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]
    assert Settings(CORS_ORIGINS="").cors_origin_list == []


def _preflight(target: FastAPI) -> dict[str, str]:
    @target.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    r = TestClient(target).options(
        "/ping",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    return dict(r.headers)


def test_cors_preflight_allowed_when_configured() -> None:
    target = FastAPI()
    configure_cors(target, ["http://localhost:4200"])
    headers = _preflight(target)
    assert headers["access-control-allow-origin"] == "http://localhost:4200"
    assert headers["access-control-allow-credentials"] == "true"
    assert "authorization" in headers["access-control-allow-headers"].lower()


def test_no_cors_headers_when_unset() -> None:
    target = FastAPI()
    configure_cors(target, [])
    assert "access-control-allow-origin" not in _preflight(target)
