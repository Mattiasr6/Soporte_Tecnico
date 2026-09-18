"""Tests S5: login JWT compatible .NET + guards. Contra postgres-dev real."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario
from app.services.tokens import (
    AUDIENCE,
    CLAIM_EMAIL,
    CLAIM_ID,
    CLAIM_NOMBRE,
    CLAIM_ROL,
    ISSUER,
    crear_token,
)

client = TestClient(app)
EMAIL = "mattias.ribera@upds.edu.bo"
PASSWORD = os.environ["SEED_PASSWORD"]
SECRET = os.environ["JWT_SECRET"]


def test_login_ok_y_claims():
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(data) == {"token", "user"}
    assert data["user"]["email"] == EMAIL
    assert data["user"]["id"] == 1
    payload = jwt.decode(
        data["token"],
        key=SECRET,
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    assert payload["iss"] == ISSUER
    assert payload["aud"] == AUDIENCE
    assert payload["sub"] == "1"
    assert payload[CLAIM_ID] == "1"
    assert payload[CLAIM_ROL] == "Tecnico"
    assert payload[CLAIM_EMAIL] == EMAIL
    assert CLAIM_NOMBRE in payload
    exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
    iat = datetime.fromtimestamp(payload["iat"], timezone.utc)
    assert (exp - iat).days == 365


def test_login_case_insensitive():
    r = client.post(
        "/api/auth/login",
        json={"email": "  MATTIAS.RIBERA@UPDS.EDU.BO ", "password": PASSWORD},
    )
    assert r.status_code == 200, r.text


def test_login_errores():
    r = client.post(
        "/api/auth/login", json={"email": "nadie@upds.edu.bo", "password": "x"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Correo no registrado"
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "mala"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Contraseña incorrecta"


def test_login_sin_password():
    with SessionLocal() as db:
        u = db.get(Usuario, 2)
        assert u is not None
        original = u.password_hash
        u.password_hash = None
        db.commit()
    try:
        r = client.post(
            "/api/auth/login",
            json={"email": "diego.orihuela@upds.edu.bo", "password": "x"},
        )
        assert r.status_code == 401
        assert "contraseña asignada" in r.json()["detail"]
    finally:
        with SessionLocal() as db:
            u = db.get(Usuario, 2)
            assert u is not None
            u.password_hash = original
            db.commit()


def test_guards_sin_token():
    assert client.get("/api/atenciones").status_code == 401
    assert client.get("/api/jerarquia/arbol").status_code == 401
    assert client.get("/api/areas").status_code == 401


def test_guards_token_malo():
    bad = {"Authorization": "Bearer abc.def.ghi"}
    assert client.get("/api/atenciones", headers=bad).status_code == 401
    otro = crear_token(1, "X", "Tecnico", EMAIL, "otra-key")
    assert (
        client.get(
            "/api/atenciones", headers={"Authorization": f"Bearer {otro}"}
        ).status_code
        == 401
    )


def test_guard_token_expirado_e_inexistente():
    ahora = datetime.now(timezone.utc)
    expirado = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": ahora - timedelta(days=400),
            "exp": ahora - timedelta(days=35),
        },
        SECRET,
        algorithm="HS256",
    )
    assert (
        client.get(
            "/api/atenciones", headers={"Authorization": f"Bearer {expirado}"}
        ).status_code
        == 401
    )
    fantasma = crear_token(999, "X", "Tecnico", "x@y.z", SECRET)
    assert (
        client.get(
            "/api/atenciones", headers={"Authorization": f"Bearer {fantasma}"}
        ).status_code
        == 401
    )
