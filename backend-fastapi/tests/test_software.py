"""Tests de seguimiento de programas: catalogo, plantillas, estados por PC."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.base import SessionLocal
from app.main import app
from app.models.lab_pc import LabPc
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.software import LabPlantilla, PcSoftware, Software, SoftwareLab
from app.models.usuario import Usuario  # noqa: F401  (registra el modelo)

client = TestClient(app)

UID_TEC = 2
UID_JEFE = 8
EMAILS = {
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}

MARK = "TEST-SW-"
AUX = "TEST-SW-AUX-"


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EQUIPO_FILE = DATA_DIR / "equipo_auxiliares.json"


@pytest.fixture
def entorno():
    respaldo = EQUIPO_FILE.read_bytes() if EQUIPO_FILE.exists() else None
    client.put("/api/laboratorios/equipo", json={"auxiliares": []}, headers=h(UID_JEFE))
    client.post(
        "/api/laboratorios/equipo", json={"nombre": f"{AUX}1"}, headers=h(UID_JEFE)
    )
    with SessionLocal() as db:
        lab = Laboratorio(
            codigo=f"{MARK}01", nombre=f"{MARK}01", activa=True, created_at=datetime.now(UTC)
        )
        db.add(lab)
        db.commit()
        db.refresh(lab)
        lab_id = lab.id
        cat = db.scalar(select(LabCategoria).where(LabCategoria.nombre == "SOFTWARE"))
        cat_id = cat.id if cat is not None else None
    yield {"lab_id": lab_id, "cat_id": cat_id}
    with SessionLocal() as db:
        pc_ids = [
            p.id
            for p in db.scalars(
                select(LabPc).where(LabPc.laboratorio_id == lab_id)
            ).all()
        ]
        if pc_ids:
            db.execute(delete(PcSoftware).where(PcSoftware.pc_id.in_(pc_ids)))
        db.execute(
            delete(LabAtencion).where(LabAtencion.auxiliar_nombre.like(f"{AUX}%"))
        )
        db.execute(delete(SoftwareLab).where(SoftwareLab.laboratorio_id == lab_id))
        db.execute(delete(LabPc).where(LabPc.laboratorio_id == lab_id))
        db.execute(
            delete(Software).where(Software.nombre.like(f"{MARK}%"))
        )
        db.execute(
            delete(LabPlantilla).where(LabPlantilla.nombre.like(f"{MARK}%"))
        )
        db.execute(delete(Laboratorio).where(Laboratorio.id == lab_id))
        db.commit()
    if respaldo is None:
        if EQUIPO_FILE.exists():
            EQUIPO_FILE.unlink()
    else:
        EQUIPO_FILE.write_bytes(respaldo)


def _sw(nombre: str, **extra: object) -> dict:
    body = {"nombre": nombre}
    body.update(extra)
    r = client.post("/api/software", json=body, headers=h(UID_JEFE))
    assert r.status_code == 201, r.text
    assert isinstance(r.json(), dict)
    return r.json()


def test_catalogo_crud_y_permisos(entorno):
    assert (
        client.post("/api/software", json={"nombre": f"{MARK}x"}, headers=h(UID_TEC)).status_code
        == 403
    )
    s = _sw(f"{MARK}Office", licencia="mixta", esencial=True)
    assert s["licencia"] == "mixta" and s["esencial"] is True
    assert (
        client.post("/api/software", json={"nombre": f"{MARK}Office"}, headers=h(UID_JEFE)).status_code
        == 400
    )
    r = client.put(f"/api/software/{s['id']}", json={"nombre": f"{MARK}Office2"}, headers=h(UID_JEFE))
    assert r.status_code == 200 and r.json()["nombre"] == f"{MARK}Office2"
    assert client.put("/api/software/999999", json={"nombre": "x"}, headers=h(UID_JEFE)).status_code == 404
    r = client.get("/api/software", headers=h(UID_TEC))
    assert r.status_code == 200 and any(x["nombre"] == f"{MARK}Office2" for x in r.json())


def test_plantillas(entorno):
    r = client.post(
        "/api/software/plantillas",
        json={"nombre": f"{MARK}Instalar", "categoria": "SOFTWARE", "descripcion": "Instalar {programa} en {pc}", "solucion": "Verificado"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = client.post(
        "/api/software/plantillas",
        json={"nombre": f"{MARK}Mala", "categoria": "NOEXISTE"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 422
    r = client.put(
        f"/api/software/plantillas/{pid}",
        json={"nombre": f"{MARK}Instalar", "categoria": "SOFTWARE", "turno": "noche2"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 400
    r = client.get("/api/software/plantillas", headers=h(UID_TEC))
    assert any(p["nombre"] == f"{MARK}Instalar" for p in r.json())


def test_matriz_lab(entorno):
    s1 = _sw(f"{MARK}A")
    s2 = _sw(f"{MARK}B")
    r = client.put(
        f"/api/software/laboratorios/{entorno['lab_id']}",
        json={"software_ids": [s1["id"], s2["id"]]},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200 and r.json()["actualizados"] == 2
    r = client.get(f"/api/software/laboratorios/{entorno['lab_id']}", headers=h(UID_TEC))
    assert {x["nombre"] for x in r.json()} == {f"{MARK}A", f"{MARK}B"}
    assert (
        client.put(
            f"/api/software/laboratorios/{entorno['lab_id']}",
            json={"software_ids": [999999]},
            headers=h(UID_JEFE),
        ).status_code
        == 400
    )


def _pc(db_lab_id: int, nombre: str) -> int:
    with SessionLocal() as db:
        pc = LabPc(
            laboratorio_id=db_lab_id, nombre=nombre, fila=0, col=0,
            activa=True, created_at=datetime.now(UTC),
        )
        db.add(pc)
        db.commit()
        db.refresh(pc)
        return pc.id


def test_marcar_estado_crea_atencion(entorno):
    sw = _sw(f"{MARK}SQL")
    client.put(
        f"/api/software/laboratorios/{entorno['lab_id']}",
        json={"software_ids": [sw["id"]]},
        headers=h(UID_JEFE),
    )
    pc_id = _pc(entorno["lab_id"], f"{MARK}PC01")
    body = {"software_id": sw["id"], "estado": "instalado", "auxiliar_nombre": f"{AUX}1"}
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "instalado"
    atencion_id = r.json()["atencion_id"]
    with SessionLocal() as db:
        at = db.get(LabAtencion, atencion_id)
        assert at is not None and at.pc_nombre == f"{MARK}PC01"
        n_antes = len(db.scalars(select(LabAtencion).where(LabAtencion.pc_nombre == f"{MARK}PC01")).all())
    # mismo estado: no duplica atencion
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(UID_TEC))
    assert r.status_code == 200 and "atencion_id" not in r.json()
    with SessionLocal() as db:
        n_despues = len(db.scalars(select(LabAtencion).where(LabAtencion.pc_nombre == f"{MARK}PC01")).all())
    assert n_antes == n_despues
    # cambio de estado: nueva atencion
    body["estado"] = "dañado"
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(UID_TEC))
    assert r.status_code == 200 and "atencion_id" in r.json()
    # historial por pc
    r = client.get(f"/api/software/atenciones-pc/{pc_id}", headers=h(UID_TEC))
    assert r.status_code == 200 and len(r.json()) == 2
    # estados listados
    r = client.get(f"/api/software/pcs/{pc_id}", headers=h(UID_TEC))
    assert r.json() == [{"software_id": sw["id"], "nombre": sw["nombre"], "estado": "dañado"}]


def test_marcar_rechazos(entorno):
    sw = _sw(f"{MARK}SQL")
    pc_id = _pc(entorno["lab_id"], f"{MARK}PC01")
    base = {"software_id": sw["id"], "estado": "instalado", "auxiliar_nombre": f"{AUX}1"}
    assert client.put("/api/software/pcs/999999", json=base, headers=h(UID_TEC)).status_code == 404
    assert client.put(f"/api/software/pcs/{pc_id}", json={**base, "estado": "roto"}, headers=h(UID_TEC)).status_code in (400, 422)
    assert client.put(f"/api/software/pcs/{pc_id}", json={**base, "auxiliar_nombre": "Nadie"}, headers=h(UID_TEC)).status_code == 400
