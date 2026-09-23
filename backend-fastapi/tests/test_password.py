"""Tests del cambio de contraseña propio, contra postgres-dev real.

Cambia la contraseña de un usuario de verdad, asi que la restaura en un `finally`:
si no, la suite siguiente no podria loguearse.
"""

import os

from fastapi.testclient import TestClient

from app.main import app

EMAIL = "mattias.ribera@upds.edu.bo"
NUEVA = "ClaveDePrueba2026*"

client = TestClient(app)


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(password: str) -> str:
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _login(password: str) -> int:
    return client.post(
        "/api/auth/login", json={"email": EMAIL, "password": password}
    ).status_code


def test_password_sin_token():
    r = client.post("/api/auth/password", json={"actual": "x", "nueva": "yyyyyyyy"})
    assert r.status_code == 401


def test_cambiar_password_ciclo_completo():
    original = os.environ["SEED_PASSWORD"]
    token = _token(original)

    corta = client.post(
        "/api/auth/password",
        json={"actual": original, "nueva": "corta"},
        headers=_h(token),
    )
    assert corta.status_code == 400
    assert "8 caracteres" in corta.json()["detail"]

    igual = client.post(
        "/api/auth/password",
        json={"actual": original, "nueva": original},
        headers=_h(token),
    )
    assert igual.status_code == 400

    equivocada = client.post(
        "/api/auth/password",
        json={"actual": "no-es-la-mia", "nueva": NUEVA},
        headers=_h(token),
    )
    assert equivocada.status_code == 401
    assert _login(original) == 200

    try:
        r = client.post(
            "/api/auth/password",
            json={"actual": original, "nueva": NUEVA},
            headers=_h(token),
        )
        assert r.status_code == 204, r.text
        assert _login(original) == 401
        assert _login(NUEVA) == 200
    finally:
        restaurado = client.post(
            "/api/auth/password",
            json={"actual": NUEVA, "nueva": original},
            headers=_h(token),
        )
        assert restaurado.status_code == 204, "no se pudo restaurar la contraseña"

    assert _login(original) == 200
