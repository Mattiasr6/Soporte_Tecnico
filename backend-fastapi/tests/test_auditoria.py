"""Auditoría: solo un Jefe puede leerla; los cambios quedan registrados."""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.usuario import Usuario  # noqa: F401  (registra el modelo)

client = TestClient(app)

UID_JEFE = 8
UID_TEC = 2
UID_MATTIAS = 1
EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
ENCARGADO = "Encargado.Auxiliar@upds.edu.bo"
_tokens: dict[int, str] = {}

MARK = "TEST-AUD-"


@pytest.fixture
def lab_aud():
    """Crea un laboratorio de prueba y lo deja limpio al salir."""
    from sqlalchemy import delete, select

    from app.db.base import SessionLocal
    from app.models.auditoria import AuditoriaCambio
    from app.models.laboratorio import Laboratorio

    def limpiar() -> None:
        with SessionLocal() as db:
            ids = [
                lab.id
                for lab in db.scalars(
                    select(Laboratorio).where(Laboratorio.codigo.like(f"{MARK}%"))
                ).all()
            ]
            if ids:
                db.execute(
                    delete(AuditoriaCambio).where(
                        AuditoriaCambio.entidad_id.in_(ids)
                    )
                )
                db.execute(delete(Laboratorio).where(Laboratorio.id.in_(ids)))
                db.commit()

    limpiar()
    yield
    limpiar()


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


def _login(email: str) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": os.environ["SEED_PASSWORD"]},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_lectura_solo_jefe():
    # Jefe: 200
    r = client.get("/api/auditoria", headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
    # Tecnico con dashboard (el dev): 200
    r = client.get("/api/auditoria", headers=h(UID_MATTIAS))
    assert r.status_code == 200, r.text
    # Tecnico comun: 403
    assert client.get("/api/auditoria", headers=h(UID_TEC)).status_code == 403
    # sin sesion: 401
    assert client.get("/api/auditoria").status_code == 401


def test_lectura_encargado_tambien_403():
    """Un Encargado gestiona los labs pero NO ve el rastro de cambios."""
    header = _login(ENCARGADO)
    assert client.get("/api/auditoria", headers=header).status_code == 403


def test_crear_lab_deja_rastro_y_encargado_puede_editar(lab_aud):
    codigo = f"{MARK}01"
    body = {"codigo": codigo, "nombre": f"{codigo} nombre"}
    r = client.post("/api/laboratorios/", json=body, headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    lab_id = r.json()["id"]

    # el rastro es visible para el Jefe
    r = client.get("/api/auditoria?entidad=laboratorio", headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    filas = [f for f in r.json() if f.get("entidad_id") == lab_id]
    assert filas, "no quedo registro de creacion"
    assert filas[0]["accion"] == "crear"
    assert codigo in filas[0]["detalle"]
    assert filas[0]["usuario_email"].endswith("@upds.edu.bo")
    assert filas[0]["rol"] == "Jefe"

    # un Encargado ahora SÍ puede editar la ficha (control total)
    header = _login(ENCARGADO)
    r = client.put(
        f"/api/laboratorios/{lab_id}",
        json={"ram": "16 GB", "capacidad": 31},
        headers=header,
    )
    assert r.status_code == 204, r.text

    # y esa edición también queda registrada, con el diff
    r = client.get("/api/auditoria?entidad=laboratorio", headers=h(UID_JEFE))
    ediciones = [
        f
        for f in r.json()
        if f.get("entidad_id") == lab_id and f["accion"] == "editar"
    ]
    assert ediciones, "no quedo registro de edicion"
    assert "ram" in ediciones[0]["detalle"]
    assert "16 GB" in ediciones[0]["detalle"]
    assert ediciones[0]["rol"] == "Encargado"

    # no se borra: no hay endpoint de borrado de laboratorios


def test_editor_de_lab_encargado_no_es_bloqueado():
    """El bug original: el Encargado guardando la ficha recibia 403."""
    header = _login(ENCARGADO)
    r = client.put(
        "/api/laboratorios/1",
        json={"ram": "8 GB"},
        headers=header,
    )
    assert r.status_code == 204, f"Encargado bloqueado: {r.status_code} {r.text}"


def test_tecnico_sigue_bloqueado_en_labs():
    r = client.put(
        "/api/laboratorios/1",
        json={"ram": "4 GB"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 403
