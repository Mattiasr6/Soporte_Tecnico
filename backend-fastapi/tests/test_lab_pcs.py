"""Tests de PCs por laboratorio (dibujo estilo sala de cine)."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models.lab_pc import LabPc
from app.models.laboratorio import LabAtencion, Laboratorio
from app.models.usuario import Usuario  # noqa: F401  (registra el modelo)

client = TestClient(app)

UID_TEC = 2
UID_JEFE = 8
EMAILS = {
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}

MARK = "TEST-PCS-"


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


@pytest.fixture
def lab():
    with SessionLocal() as db:
        row = Laboratorio(
            codigo=f"{MARK}01",
            nombre=f"{MARK}01 nombre",
            activa=True,
            filas_pc=0,
            cols_pc=0,
            created_at=datetime.now(UTC),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        lab_id = row.id
    yield lab_id
    with SessionLocal() as db:
        db.query(LabPc).filter(LabPc.laboratorio_id == lab_id).delete()
        db.query(LabAtencion).filter(LabAtencion.laboratorio_id == lab_id).delete()
        db.query(Laboratorio).filter(Laboratorio.id == lab_id).delete()
        db.commit()


def _put(lab_id: int, body: dict, uid: int = UID_JEFE):
    return client.put(f"/api/laboratorios/{lab_id}/pcs", json=body, headers=h(uid))


def test_get_vacio(lab):
    r = client.get(f"/api/laboratorios/{lab}/pcs", headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    assert r.json() == {"filas": 0, "cols": 0, "pcs": []}


def test_put_y_get(lab):
    body = {
        "filas": 2,
        "cols": 3,
        "pcs": [
            {"nombre": "SCPC 901", "fila": 0, "col": 0},
            {"nombre": "SCPC 902", "fila": 0, "col": 2, "activa": False},
            {"nombre": "SCPC 903", "fila": 1, "col": 1},
        ],
    }
    r = _put(lab, body)
    assert r.status_code == 200, r.text
    assert r.json()["filas"] == 2 and r.json()["cols"] == 3
    r = client.get(f"/api/laboratorios/{lab}/pcs", headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    assert [p["nombre"] for p in r.json()["pcs"]] == [
        "SCPC 901",
        "SCPC 902",
        "SCPC 903",
    ]
    assert r.json()["pcs"][1]["activa"] is False


def test_put_reemplaza_todo(lab):
    _put(
        lab,
        {"filas": 1, "cols": 2, "pcs": [{"nombre": "PC A", "fila": 0, "col": 0}]},
    )
    r = _put(
        lab,
        {"filas": 1, "cols": 1, "pcs": [{"nombre": "PC B", "fila": 0, "col": 0}]},
    )
    assert [p["nombre"] for p in r.json()["pcs"]] == ["PC B"]


def test_rechazos(lab):
    assert (
        _put(lab, {"filas": 1, "cols": 1, "pcs": []}, uid=UID_TEC).status_code == 403
    )
    assert _put(lab, {"filas": 31, "cols": 1, "pcs": []}).status_code == 400
    r = _put(
        lab, {"filas": 0, "cols": 0, "pcs": [{"nombre": "X", "fila": 0, "col": 0}]}
    )
    assert r.status_code == 400
    r = _put(lab, {"filas": 2, "cols": 2, "pcs": [{"nombre": "X", "fila": 5, "col": 0}]})
    assert r.status_code == 400
    r = _put(
        lab,
        {
            "filas": 2,
            "cols": 2,
            "pcs": [
                {"nombre": "PC 1", "fila": 0, "col": 0},
                {"nombre": "pc 1", "fila": 1, "col": 1},
            ],
        },
    )
    assert r.status_code == 400
    r = _put(
        lab,
        {
            "filas": 2,
            "cols": 2,
            "pcs": [
                {"nombre": "PC 1", "fila": 0, "col": 0},
                {"nombre": "PC 2", "fila": 0, "col": 0},
            ],
        },
    )
    assert r.status_code == 400
    r = _put(
        lab, {"filas": 1, "cols": 1, "pcs": [{"nombre": "   ", "fila": 0, "col": 0}]}
    )
    assert r.status_code == 400


def test_lab_inexistente():
    r = client.get("/api/laboratorios/999999/pcs", headers=h(UID_JEFE))
    assert r.status_code == 404
