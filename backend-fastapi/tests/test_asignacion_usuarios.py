"""T8: asignacion user management (old Supabase `perfiles` screen) on Soporte users.

Identity (create, rol, activo, nombre, password) is written to `Usuarios` through
the same functions `/api/usuarios` uses; asignacion-only fields stay in
`horarios.perfiles`. Only admin (Jefe) may manage users, like the old
`fn_crear_usuario`/`fn_cambiar_password`/`perfiles_editar` (fn_es_admin).

Self-contained: every row is created here and deleted at teardown.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario
from app.services.tokens import crear_token

client = TestClient(app)
DOMAIN = "test-asig-usuarios.local"
BASE = "/api/asignacion/usuarios"
PASSWORD = "ClaveSegura123"


def _cleanup() -> None:
    with SessionLocal() as db:
        ids = list(
            db.execute(
                text('select "Id" from "Usuarios" where "Email" like :d'),
                {"d": f"%@{DOMAIN}"},
            ).scalars()
        )
        for uid in ids:
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


@pytest.fixture
def make_usuario() -> Iterator[Callable[..., Usuario]]:
    def _make(role: str, activo: bool = True) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"Prueba {role}",
                role=role,
                activo=activo,
                password_hash=bcrypt.hashpw(
                    PASSWORD.encode(), bcrypt.gensalt()
                ).decode(),
                created_at=now,
                updated_at=now,
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
            db.expunge(usuario)
        return usuario

    yield _make
    _cleanup()


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


def _usuario(uid: int) -> Usuario:
    with SessionLocal() as db:
        usuario = db.get(Usuario, uid)
        assert usuario is not None
        db.expunge(usuario)
        return usuario


def _perfil(uid: int) -> dict:
    with SessionLocal() as db:
        row = (
            db.execute(
                text(
                    "select id, rol, activo, nombre_completo, turno_habitual,"
                    " sabado_rotativo from horarios.perfiles where usuario_id = :uid"
                ),
                {"uid": uid},
            )
            .mappings()
            .one()
        )
        return dict(row)


def _listed(jefe: Usuario) -> dict[int, dict]:
    r = client.get(BASE, headers=_auth(jefe))
    assert r.status_code == 200, r.text
    return {u["usuario_id"]: u for u in r.json()}


def _perfil_id(jefe: Usuario, uid: int) -> str:
    return _listed(jefe)[uid]["id"]


# --- auth / permissions -------------------------------------------------------


def test_without_token_is_401() -> None:
    fake = "00000000-0000-0000-0000-000000000000"
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json={}).status_code == 401
    assert client.patch(f"{BASE}/{fake}", json={}).status_code == 401
    assert client.post(f"{BASE}/{fake}/password", json={}).status_code == 401


@pytest.mark.parametrize(
    "role", ["Encargado", "Auxiliar", "Decano", "Invitado", "Tecnico"]
)
def test_non_admin_is_403(make_usuario, role: str) -> None:
    jefe = make_usuario("Jefe")
    actor = make_usuario(role)
    target = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, target.id)
    headers = _auth(actor)
    assert client.get(BASE, headers=headers).status_code == 403
    r = client.post(
        BASE,
        json={
            "nombre_completo": "X",
            "correo": f"nope@{DOMAIN}",
            "password": PASSWORD,
            "rol": "auxiliar",
        },
        headers=headers,
    )
    assert r.status_code == 403, r.text
    r = client.patch(f"{BASE}/{perfil_id}", json={"activo": False}, headers=headers)
    assert r.status_code == 403, r.text
    r = client.post(
        f"{BASE}/{perfil_id}/password", json={"password": PASSWORD}, headers=headers
    )
    assert r.status_code == 403, r.text
    assert _usuario(target.id).activo is True


# --- list ----------------------------------------------------------------------


def test_list_includes_every_soporte_user_with_mapped_rol(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    tecnico = make_usuario("Tecnico")  # never opened asignacion: no perfil yet
    decano = make_usuario("Decano")
    inactivo = make_usuario("Auxiliar", activo=False)
    listed = _listed(jefe)
    assert set(listed[tecnico.id]) == {
        "id",
        "usuario_id",
        "nombre_completo",
        "correo",
        "rol",
        "role",
        "activo",
        "turno_habitual",
        "sabado_rotativo",
    }
    assert listed[tecnico.id]["rol"] == "invitado"
    assert listed[tecnico.id]["role"] == "Tecnico"
    assert listed[tecnico.id]["correo"] == tecnico.email
    assert listed[decano.id]["rol"] == "decano"
    assert listed[inactivo.id]["activo"] is False
    assert listed[jefe.id]["rol"] == "admin"


# --- create --------------------------------------------------------------------


def test_create_makes_a_soporte_user_that_can_log_in(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    correo = f"Nuevo-{uuid4().hex[:6]}@{DOMAIN}"
    r = client.post(
        BASE,
        json={
            "nombre_completo": "  Nuevo Decano ",
            "correo": correo,
            "password": PASSWORD,
            "rol": "decano",
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rol"] == "decano"
    assert body["role"] == "Decano"
    assert body["activo"] is True
    assert body["correo"] == correo.lower()
    assert body["nombre_completo"] == "Nuevo Decano"
    usuario = _usuario(body["usuario_id"])
    assert usuario.role == "Decano"
    assert str(_perfil(usuario.id)["id"]) == body["id"]
    r = client.post("/api/auth/login", json={"email": correo, "password": PASSWORD})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    ("rol", "role"),
    [("admin", "Jefe"), ("encargado", "Encargado"), ("auxiliar", "Auxiliar")],
)
def test_create_translates_rol_to_soporte_role(make_usuario, rol, role) -> None:
    jefe = make_usuario("Jefe")
    r = client.post(
        BASE,
        json={
            "nombre_completo": "Rol",
            "correo": f"{rol}-{uuid4().hex[:6]}@{DOMAIN}",
            "password": PASSWORD,
            "rol": rol,
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 201, r.text
    assert _usuario(r.json()["usuario_id"]).role == role


def test_create_rejects_invitado_like_fn_crear_usuario(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    r = client.post(
        BASE,
        json={
            "nombre_completo": "X",
            "correo": f"inv@{DOMAIN}",
            "password": PASSWORD,
            "rol": "invitado",
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 422, r.text


def test_create_duplicate_correo_is_409(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    existente = make_usuario("Tecnico")
    r = client.post(
        BASE,
        json={
            "nombre_completo": "X",
            "correo": existente.email.upper(),
            "password": PASSWORD,
            "rol": "auxiliar",
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 409, r.text


def test_create_short_password_is_400(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    r = client.post(
        BASE,
        json={
            "nombre_completo": "X",
            "correo": f"corta@{DOMAIN}",
            "password": "123",
            "rol": "auxiliar",
        },
        headers=_auth(jefe),
    )
    assert r.status_code == 400, r.text


# --- update --------------------------------------------------------------------


def test_change_rol_writes_soporte_role(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(
        f"{BASE}/{perfil_id}", json={"rol": "encargado"}, headers=_auth(jefe)
    )
    assert r.status_code == 200, r.text
    assert r.json()["rol"] == "encargado"
    assert _usuario(aux.id).role == "Encargado"
    assert _perfil(aux.id)["rol"] == "encargado"


def test_tecnico_is_not_downgraded_when_rol_stays_invitado(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    tecnico = make_usuario("Tecnico")
    perfil_id = _perfil_id(jefe, tecnico.id)
    r = client.patch(
        f"{BASE}/{perfil_id}",
        json={"rol": "invitado", "sabado_rotativo": True},
        headers=_auth(jefe),
    )
    assert r.status_code == 200, r.text
    assert _usuario(tecnico.id).role == "Tecnico"
    assert r.json()["role"] == "Tecnico"


def test_invitado_rol_sets_soporte_invitado(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(
        f"{BASE}/{perfil_id}", json={"rol": "invitado"}, headers=_auth(jefe)
    )
    assert r.status_code == 200, r.text
    assert _usuario(aux.id).role == "Invitado"


def test_asignacion_fields_stay_in_perfiles(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(
        f"{BASE}/{perfil_id}",
        json={"turno_habitual": "MD", "sabado_rotativo": True},
        headers=_auth(jefe),
    )
    assert r.status_code == 200, r.text
    perfil = _perfil(aux.id)
    assert perfil["turno_habitual"] == "MD"
    assert perfil["sabado_rotativo"] is True
    assert _usuario(aux.id).role == "Auxiliar"
    r = client.patch(
        f"{BASE}/{perfil_id}", json={"turno_habitual": None}, headers=_auth(jefe)
    )
    assert r.status_code == 200, r.text
    assert _perfil(aux.id)["turno_habitual"] is None


def test_invalid_turno_is_422(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(
        f"{BASE}/{perfil_id}", json={"turno_habitual": "X"}, headers=_auth(jefe)
    )
    assert r.status_code == 422, r.text


def test_deactivate_and_rename_write_usuarios(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(
        f"{BASE}/{perfil_id}",
        json={"activo": False, "nombre_completo": " Nombre Nuevo "},
        headers=_auth(jefe),
    )
    assert r.status_code == 200, r.text
    usuario = _usuario(aux.id)
    assert usuario.activo is False
    assert usuario.display_name == "Nombre Nuevo"
    perfil = _perfil(aux.id)
    assert perfil["activo"] is False
    assert perfil["nombre_completo"] == "Nombre Nuevo"


def test_admin_cannot_change_own_rol_or_deactivate_self(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    perfil_id = _perfil_id(jefe, jefe.id)
    r = client.patch(
        f"{BASE}/{perfil_id}", json={"rol": "auxiliar"}, headers=_auth(jefe)
    )
    assert r.status_code == 400, r.text
    r = client.patch(f"{BASE}/{perfil_id}", json={"activo": False}, headers=_auth(jefe))
    assert r.status_code == 400, r.text
    assert _usuario(jefe.id).role == "Jefe"
    assert _usuario(jefe.id).activo is True


def test_unknown_perfil_is_404(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    fake = "00000000-0000-0000-0000-000000000000"
    r = client.patch(f"{BASE}/{fake}", json={"activo": False}, headers=_auth(jefe))
    assert r.status_code == 404, r.text
    r = client.post(
        f"{BASE}/{fake}/password", json={"password": PASSWORD}, headers=_auth(jefe)
    )
    assert r.status_code == 404, r.text


def test_unknown_field_is_422(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    r = client.patch(f"{BASE}/{perfil_id}", json={"correo": "x@y"}, headers=_auth(jefe))
    assert r.status_code == 422, r.text


# --- password ------------------------------------------------------------------


def test_change_password(make_usuario) -> None:
    jefe = make_usuario("Jefe")
    aux = make_usuario("Auxiliar")
    perfil_id = _perfil_id(jefe, aux.id)
    nueva = "OtraClave4567"
    r = client.post(
        f"{BASE}/{perfil_id}/password", json={"password": nueva}, headers=_auth(jefe)
    )
    assert r.status_code == 204, r.text
    r = client.post("/api/auth/login", json={"email": aux.email, "password": nueva})
    assert r.status_code == 200, r.text
    r = client.post(
        f"{BASE}/{perfil_id}/password", json={"password": "123"}, headers=_auth(jefe)
    )
    assert r.status_code == 400, r.text
