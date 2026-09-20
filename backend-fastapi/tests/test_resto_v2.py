"""Tests S6 contra postgres-dev real. Limpieza total al final."""

import os

from app.db.base import SessionLocal
from app.main import app
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.services.estados import estado_efectivo
from fastapi.testclient import TestClient

UID_MATTIAS = 1
UID_DIEGO = 2
UID_JEFE = 8

EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}

client = TestClient(app)


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


def test_estado_efectivo_puro():
    from datetime import datetime, timezone

    ahora = datetime.now(timezone.utc)
    assert estado_efectivo("Ausente", None, ahora) == "ausente"
    assert estado_efectivo("Extraturno", None, ahora) == "extraturno"
    assert estado_efectivo("Disponible", None, ahora) == "disponible"


def test_horarios_crud_2099():
    dto = {
        "usuario_id": UID_DIEGO,
        "label": "TEST-S6",
        "hora_inicio1": "08:00",
        "hora_fin1": "16:00",
        "hora_inicio2": None,
        "hora_fin2": None,
        "mes": 1,
        "anio": 2099,
    }
    try:
        assert (
            client.post("/api/horarios", json=dto, headers=h(UID_DIEGO)).status_code
            == 403
        )
        assert (
            client.post(
                "/api/horarios",
                json={**dto, "usuario_id": UID_JEFE},
                headers=h(UID_JEFE),
            ).status_code
            == 400
        )
        assert (
            client.post("/api/horarios", json=dto, headers=h(UID_JEFE)).status_code
            == 204
        )
        rows = client.get(
            "/api/horarios",
            params={"mes": 1, "anio": 2099},
            headers=h(UID_JEFE),
        ).json()
        assert len(rows) == 1
        assert rows[0]["label"] == "TEST-S6"
        assert rows[0]["nombre"] == "Diego Orihuela Herrera"
        hid = rows[0]["id"]
        propios = client.get(
            "/api/horarios",
            params={"mes": 1, "anio": 2099},
            headers=h(UID_DIEGO),
        ).json()
        assert len(propios) == 1
        dto2 = {**dto, "label": "TEST-S6-B"}
        assert (
            client.post("/api/horarios", json=dto2, headers=h(UID_JEFE)).status_code
            == 204
        )
        rows = client.get(
            "/api/horarios",
            params={"mes": 1, "anio": 2099},
            headers=h(UID_JEFE),
        ).json()
        assert len(rows) == 1 and rows[0]["label"] == "TEST-S6-B"
        assert (
            client.delete(f"/api/horarios/{hid}", headers=h(UID_DIEGO)).status_code
            == 403
        )
        assert (
            client.delete(f"/api/horarios/{hid}", headers=h(UID_JEFE)).status_code
            == 204
        )
        assert (
            client.delete(f"/api/horarios/{hid}", headers=h(UID_JEFE)).status_code
            == 404
        )
    finally:
        with SessionLocal() as db:
            for x in (
                db.query(Horario).filter(Horario.mes == 1, Horario.anio == 2099).all()
            ):
                db.delete(x)
            db.commit()


def test_cobertura_forma():
    r = client.get("/api/horarios/cobertura", headers=h(UID_DIEGO))
    assert r.status_code == 200
    data = r.json()
    assert [f["franja"] for f in data["cobertura"]] == [
        "Manana",
        "Medio dia",
        "Tarde",
        "Noche",
    ]
    assert all("hora" in f and "tecnicos" in f for f in data["cobertura"])


def test_usuarios_lista_y_me():
    rows = client.get("/api/usuarios", headers=h(UID_DIEGO)).json()
    assert len(rows) > 0
    assert all(u["role"] in ("Tecnico", "Jefe") for u in rows)
    assert all(
        u["estado_actual"] in ("disponible", "ocupado", "ausente", "extraturno")
        for u in rows
    )
    me = client.get("/api/usuarios/me", headers=h(UID_DIEGO)).json()
    assert me["id"] == UID_DIEGO


def test_especialidad_permiso_y_restore():
    with SessionLocal() as db:
        diego = db.get(Usuario, UID_DIEGO)
        assert diego is not None
        original = diego.especialidad
    try:
        assert (
            client.patch(
                f"/api/usuarios/{UID_DIEGO}/especialidad",
                json={"especialidad": "TEST-S6"},
                headers=h(UID_DIEGO),
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/usuarios/{UID_DIEGO}/especialidad",
                json={"especialidad": "TEST-S6"},
                headers=h(UID_JEFE),
            ).status_code
            == 204
        )
        rows = client.get("/api/usuarios", headers=h(UID_JEFE)).json()
        assert (
            next(u for u in rows if u["id"] == UID_DIEGO)["especialidad"] == "TEST-S6"
        )
    finally:
        with SessionLocal() as db:
            u = db.get(Usuario, UID_DIEGO)
            assert u is not None
            u.especialidad = original
            db.commit()


def test_notas_propias_y_restore():
    with SessionLocal() as db:
        diego = db.get(Usuario, UID_DIEGO)
        assert diego is not None
        original = diego.notas
    try:
        assert (
            client.put(
                "/api/usuarios/notas",
                json={"contenido": "TEST-S6-nota"},
                headers=h(UID_DIEGO),
            ).status_code
            == 204
        )
        assert client.get("/api/usuarios/notas", headers=h(UID_DIEGO)).json() == {
            "contenido": "TEST-S6-nota"
        }
    finally:
        with SessionLocal() as db:
            u = db.get(Usuario, UID_DIEGO)
            assert u is not None
            u.notas = original
            db.commit()


def test_estado_transiciones_y_restore():
    assert (
        client.patch(
            "/api/usuarios/estado",
            json={"estado_actual": "ausente"},
            headers=h(UID_DIEGO),
        ).status_code
        == 400
    )
    assert (
        client.patch(
            "/api/usuarios/estado",
            json={"estado_actual": "invalido"},
            headers=h(UID_DIEGO),
        ).status_code
        == 400
    )
    try:
        assert (
            client.patch(
                "/api/usuarios/estado",
                json={"estado_actual": "DISPONIBLE"},
                headers=h(UID_DIEGO),
            ).status_code
            == 204
        )
        me = client.get("/api/usuarios/me", headers=h(UID_DIEGO)).json()
        assert me["estado_actual"] in ("disponible", "extraturno")
    finally:
        with SessionLocal() as db:
            u = db.get(Usuario, UID_DIEGO)
            assert u is not None
            u.estado_actual = "Ausente"
            db.commit()


def test_announcements_flujo_y_restore():
    assert client.get("/api/announcements").status_code == 200
    inicial = client.get("/api/announcements").json()
    try:
        assert (
            client.post(
                "/api/announcements",
                json={"message": "x"},
                headers=h(UID_DIEGO),
            ).status_code
            == 403
        )
        r = client.post(
            "/api/announcements",
            json={"message": "  TEST-S6  "},
            headers=h(UID_JEFE),
        )
        assert r.status_code == 200
        assert r.json() == {"message": "TEST-S6"}
        r = client.post(
            "/api/announcements", json={"message": "   "}, headers=h(UID_JEFE)
        )
        assert r.json() == {"message": None}
    finally:
        client.post(
            "/api/announcements",
            json={"message": inicial["message"]},
            headers=h(UID_JEFE),
        )
        assert client.get("/api/announcements").json() == inicial
