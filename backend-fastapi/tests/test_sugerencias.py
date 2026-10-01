"""Tests del buzón de sugerencias contra la base de prueba real."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.base import SessionLocal
from app.main import app
from app.models.sugerencia import Sugerencia

UID_TECNICO = 2  # Diego: Tecnico sin dashboard
UID_JEFE = 8  # Josue: Jefe
MARK = "TEST-SUG-"

client = TestClient(app)

EMAILS = {
    UID_TECNICO: "diego.orihuela@upds.edu.bo",
    UID_JEFE: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


def _limpiar() -> None:
    with SessionLocal() as db:
        db.execute(delete(Sugerencia).where(Sugerencia.texto.like(f"{MARK}%")))
        db.commit()


@pytest.fixture(autouse=True)
def sin_residuos():
    _limpiar()
    yield
    _limpiar()


def _crear(texto: str) -> dict[str, object]:
    r = client.post("/api/sugerencias", json={"texto": texto}, headers=h(UID_TECNICO))
    assert r.status_code == 201, r.text
    return r.json()


def test_auth_requerida():
    assert client.get("/api/sugerencias").status_code == 401
    assert client.post("/api/sugerencias", json={"texto": "x"}).status_code == 401


def test_crear_y_listar():
    creada = _crear(f"{MARK}capacitar en redes")
    assert creada["usuario_id"] == UID_TECNICO
    assert creada["estado"] == "pendiente"
    assert creada["autor"]
    assert creada["texto"] == f"{MARK}capacitar en redes"

    lista = client.get("/api/sugerencias", headers=h(UID_JEFE))
    assert lista.status_code == 200
    filas = lista.json()
    fila = next(s for s in filas if s["id"] == creada["id"])
    assert fila["texto"] == f"{MARK}capacitar en redes"
    assert fila["autor"] == creada["autor"]
    assert filas[0]["id"] == creada["id"]  # las más nuevas primero


def test_texto_vacio_o_solo_espacios():
    vacio = client.post("/api/sugerencias", json={"texto": ""}, headers=h(UID_TECNICO))
    assert vacio.status_code == 422
    espacios = client.post(
        "/api/sugerencias", json={"texto": "   "}, headers=h(UID_TECNICO)
    )
    assert espacios.status_code == 400


def test_patch_solo_jefe():
    creada = _crear(f"{MARK}revisar esto")
    r = client.patch(
        f"/api/sugerencias/{creada['id']}",
        json={"estado": "revisada"},
        headers=h(UID_TECNICO),
    )
    assert r.status_code == 403

    r = client.patch(
        f"/api/sugerencias/{creada['id']}",
        json={"estado": "revisada"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "revisada"


def test_patch_estado_invalido():
    creada = _crear(f"{MARK}estado raro")
    r = client.patch(
        f"/api/sugerencias/{creada['id']}",
        json={"estado": "aprobada"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 400


def test_patch_inexistente():
    r = client.patch(
        "/api/sugerencias/99999999",
        json={"estado": "descartada"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 404
