"""Tests S7: WS nativo + broadcasts. Contra postgres-dev real, estados restaurados."""

import os

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario

UID_MATTIAS = 1
UID_DIEGO = 2
UID_JEFE = 8

EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}

client = TestClient(app)


def token(uid: int) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def h(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(uid)}"}


def set_estado(uid: int, estado: str) -> None:
    with SessionLocal() as db:
        u = db.get(Usuario, uid)
        assert u is not None
        u.estado_actual = estado
        db.commit()


def test_4401_sin_token():
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws"):
        pass
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws", params={"access_token": "malo"}),
    ):
        pass


def test_connect_flip_y_disconnect():
    set_estado(UID_DIEGO, "Ausente")
    try:
        with client.websocket_connect(
            "/ws", params={"access_token": token(UID_MATTIAS)}
        ) as obs:
            obs.receive_json()  # propio connect de Mattias
            with client.websocket_connect(
                "/ws", params={"access_token": token(UID_DIEGO)}
            ) as diego:
                propio = diego.receive_json()
                assert propio["type"] == "status_changed"
                assert propio["usuario_id"] == UID_DIEGO
                assert propio["estado"] == "disponible"
                ajeno = obs.receive_json()
                assert ajeno["usuario_id"] == UID_DIEGO
            # Diego cerró su última conexión → ausente
            cierre = obs.receive_json()
            assert cierre["type"] == "status_changed"
            assert cierre["usuario_id"] == UID_DIEGO
            assert cierre["estado"] == "ausente"
    finally:
        set_estado(UID_DIEGO, "Ausente")


def test_chat_entre_conexiones():
    with client.websocket_connect(
        "/ws", params={"access_token": token(UID_MATTIAS)}
    ) as a:
        a.receive_json()
        with client.websocket_connect(
            "/ws", params={"access_token": token(UID_DIEGO)}
        ) as b:
            b.receive_json()
            a.receive_json()
            a.send_json({"type": "send_message", "message": "hola TEST-S7"})
            propio = a.receive_json()
            ajeno = b.receive_json()
            assert propio["type"] == ajeno["type"] == "receive_message"
            assert ajeno["message"] == "hola TEST-S7"
            assert ajeno["nombre"] == "Mattias Ribera Rojas"
            assert "timestamp" in ajeno


def test_rest_emiten_broadcast():
    inicial = client.get("/api/announcements").json()
    set_estado(UID_DIEGO, "Ausente")
    try:
        with client.websocket_connect(
            "/ws", params={"access_token": token(UID_MATTIAS)}
        ) as obs:
            obs.receive_json()
            assert (
                client.patch(
                    "/api/usuarios/estado",
                    json={"estado_actual": "disponible", "motivo": "TEST-S7"},
                    headers=h(UID_DIEGO),
                ).status_code
                == 204
            )
            ev = obs.receive_json()
            assert ev["type"] == "status_changed"
            assert ev["usuario_id"] == UID_DIEGO
            assert ev["motivo"] == "TEST-S7"
            assert (
                client.post(
                    "/api/announcements",
                    json={"message": "TEST-S7-ann"},
                    headers=h(UID_JEFE),
                ).status_code
                == 200
            )
            ann = obs.receive_json()
            assert ann == {"type": "receive_announcement", "message": "TEST-S7-ann"}
    finally:
        set_estado(UID_DIEGO, "Ausente")
        client.post(
            "/api/announcements",
            json={"message": inicial["message"]},
            headers=h(UID_JEFE),
        )
