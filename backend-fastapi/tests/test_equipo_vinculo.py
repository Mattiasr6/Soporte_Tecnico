"""Vínculo nómina ↔ cuenta: cada Auxiliar/Encargado firma con su propia cuenta.

La nómina (data/equipo_auxiliares.json) se respalda y restaura en cada test, y los
usuarios de prueba se crean con email bajo DOMINIO y se borran al salir.
"""

import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.base import SessionLocal
from app.main import app
from app.models.lab_pc import LabPc
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.novedad import Novedad
from app.models.software import PcSoftware, Software, SoftwareLab
from app.models.usuario import Usuario
from app.services.tokens import crear_token

client = TestClient(app)

UID_TEC = 2
UID_JEFE = 8
DOMINIO = "test-vinculo.local"
AUX = "TEST-VIN-AUX-"
MARK = "TEST-VIN-"
SIN_VINCULO = "Tu cuenta no está vinculada a la nómina"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EQUIPO_FILE = DATA_DIR / "equipo_auxiliares.json"
HORARIOS_FILE = DATA_DIR / "horarios_auxiliares.json"


def h(uid: int) -> dict[str, str]:
    with SessionLocal() as db:
        u = db.get(Usuario, uid)
        assert u is not None, f"usuario {uid} no existe en la base de pruebas"
        token = crear_token(
            u.id, u.display_name, u.role, u.email, os.environ["JWT_SECRET"]
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def nomina():
    respaldo = {
        p: p.read_bytes() if p.exists() else None for p in (EQUIPO_FILE, HORARIOS_FILE)
    }
    r = client.put(
        "/api/laboratorios/equipo",
        json={
            "auxiliares": [
                {"nombre": f"{AUX}Ana"},
                {"nombre": f"{AUX}Beto"},
                {"nombre": f"{AUX}Ceci", "encargado": True},
            ]
        },
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    yield
    for ruta, contenido in respaldo.items():
        if contenido is None:
            if ruta.exists():
                ruta.unlink()
        else:
            ruta.write_bytes(contenido)


@pytest.fixture
def usuarios():
    creados: list[int] = []

    def _crear(nombre: str, role: str = "Auxiliar") -> int:
        r = client.post(
            "/api/usuarios",
            json={
                "email": f"{nombre.lower()}@{DOMINIO}",
                "display_name": f"Cuenta {nombre}",
                "role": role,
            },
            headers=h(UID_JEFE),
        )
        assert r.status_code == 201, r.text
        creados.append(r.json()["id"])
        return r.json()["id"]

    yield _crear

    with SessionLocal() as db:
        db.execute(delete(LabAtencion).where(LabAtencion.usuario_id.in_(creados)))
        db.execute(delete(Novedad).where(Novedad.usuario_id.in_(creados)))
        for uid in creados:
            u = db.get(Usuario, uid)
            if u is not None:
                db.delete(u)
        db.commit()


def _vincular(nombre: str, usuario_id: int | None, uid: int = UID_JEFE):
    return client.post(
        "/api/laboratorios/equipo/vincular",
        json={"nombre": nombre, "usuario_id": usuario_id},
        headers=h(uid),
    )


def _miembro(body: dict[str, Any], nombre: str) -> dict[str, Any]:
    return next(m for m in body["auxiliares"] if m["nombre"] == nombre)


# --- vincular ---------------------------------------------------------------


def test_vincular_jefe_ok_y_persistente(nomina, usuarios):
    uid = usuarios("ana")
    r = _vincular(f"{AUX.lower()}ana", uid)
    assert r.status_code == 200, r.text
    assert _miembro(r.json(), f"{AUX}Ana")["usuario_id"] == uid
    assert _miembro(r.json(), f"{AUX}Beto")["usuario_id"] is None
    guardado = json.loads(EQUIPO_FILE.read_text(encoding="utf-8"))
    assert (
        next(m for m in guardado["auxiliares"] if m["nombre"] == f"{AUX}Ana")[
            "usuario_id"
        ]
        == uid
    )
    # las entradas sin vínculo no ganan la clave en disco
    assert "usuario_id" not in next(
        m for m in guardado["auxiliares"] if m["nombre"] == f"{AUX}Beto"
    )


def test_vincular_no_jefe_403(nomina, usuarios):
    uid = usuarios("ana")
    assert _vincular(f"{AUX}Ana", uid, uid=UID_TEC).status_code == 403
    enc = usuarios("ceci", role="Encargado")
    assert _vincular(f"{AUX}Ana", uid, uid=enc).status_code == 403


def test_vincular_validaciones(nomina, usuarios):
    uid = usuarios("ana")
    assert _vincular(f"{AUX}Ana", UID_TEC).status_code == 400  # rol Tecnico
    assert _vincular(f"{AUX}Nadie", uid).status_code == 404
    assert _vincular(f"{AUX}Ana", 99999999).status_code == 404
    with SessionLocal() as db:
        u = db.get(Usuario, uid)
        assert u is not None
        u.activo = False
        db.commit()
    assert _vincular(f"{AUX}Ana", uid).status_code == 400


def test_revincular_mueve_y_desvincular(nomina, usuarios):
    uid = usuarios("ana")
    assert _vincular(f"{AUX}Ana", uid).status_code == 200
    r = _vincular(f"{AUX}Beto", uid)
    assert r.status_code == 200, r.text
    assert _miembro(r.json(), f"{AUX}Ana")["usuario_id"] is None
    assert _miembro(r.json(), f"{AUX}Beto")["usuario_id"] == uid
    r = _vincular(f"{AUX}Beto", None)
    assert r.status_code == 200, r.text
    assert all(m["usuario_id"] is None for m in r.json()["auxiliares"])


def test_escrituras_de_nomina_conservan_vinculo(nomina, usuarios):
    uid = usuarios("ana")
    assert _vincular(f"{AUX}Ana", uid).status_code == 200
    r = client.post(
        "/api/laboratorios/equipo/encargado",
        json={"nombre": f"{AUX}Ana"},
        headers=h(UID_JEFE),
    )
    assert _miembro(r.json(), f"{AUX}Ana")["usuario_id"] == uid
    r = client.post(
        "/api/laboratorios/equipo", json={"nombre": f"{AUX}Dani"}, headers=h(UID_JEFE)
    )
    assert r.status_code == 200, r.text
    # el PUT no trae usuario_id (o trae otro): el vínculo se conserva por nombre
    r = client.put(
        "/api/laboratorios/equipo",
        json={
            "auxiliares": [
                {"nombre": f"{AUX}Ana", "activo": False, "usuario_id": UID_TEC},
                {"nombre": f"{AUX}Beto", "usuario_id": uid},
            ]
        },
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    assert _miembro(r.json(), f"{AUX}Ana")["usuario_id"] == uid
    assert _miembro(r.json(), f"{AUX}Beto")["usuario_id"] is None
    body = client.get("/api/laboratorios/equipo", headers=h(UID_TEC)).json()
    assert _miembro(body, f"{AUX}Ana")["usuario_id"] == uid


def test_entradas_sin_usuario_id_siguen_listando_y_exportando(nomina):
    EQUIPO_FILE.write_text(
        json.dumps({"auxiliares": [{"nombre": f"{AUX}Viejo", "activo": True}]}),
        encoding="utf-8",
    )
    body = client.get("/api/laboratorios/equipo", headers=h(UID_TEC)).json()
    assert body["auxiliares"] == [
        {
            "nombre": f"{AUX}Viejo",
            "activo": True,
            "encargado": False,
            "usuario_id": None,
        }
    ]
    for tipo in ("semanal", "sabado"):
        r = client.get(
            f"/api/laboratorios/horarios/export.xlsx?tipo={tipo}", headers=h(UID_JEFE)
        )
        assert r.status_code == 200, r.text


# --- equipo/yo --------------------------------------------------------------


def test_equipo_yo(nomina, usuarios):
    uid = usuarios("ceci", role="Encargado")
    r = client.get("/api/laboratorios/equipo/yo", headers=h(uid))
    assert r.status_code == 404
    assert SIN_VINCULO in r.json()["detail"]
    assert _vincular(f"{AUX}Ceci", uid).status_code == 200
    r = client.get("/api/laboratorios/equipo/yo", headers=h(uid))
    assert r.status_code == 200, r.text
    assert r.json() == {"nombre": f"{AUX}Ceci", "encargado": True, "activo": True}


# --- autoría por cuenta -----------------------------------------------------


@pytest.fixture
def lab():
    with SessionLocal() as db:
        fila = Laboratorio(
            codigo=f"{MARK}01",
            nombre=f"{MARK}01",
            activa=True,
            created_at=datetime.now(UTC),
        )
        db.add(fila)
        db.commit()
        db.refresh(fila)
        lab_id = fila.id
    yield lab_id
    with SessionLocal() as db:
        pcs = [
            p.id
            for p in db.scalars(select(LabPc).where(LabPc.laboratorio_id == lab_id))
        ]
        if pcs:
            db.execute(delete(PcSoftware).where(PcSoftware.pc_id.in_(pcs)))
        db.execute(delete(LabAtencion).where(LabAtencion.laboratorio_id == lab_id))
        db.execute(delete(SoftwareLab).where(SoftwareLab.laboratorio_id == lab_id))
        db.execute(delete(LabPc).where(LabPc.laboratorio_id == lab_id))
        db.execute(delete(Software).where(Software.nombre.like(f"{MARK}%")))
        db.execute(delete(Laboratorio).where(Laboratorio.id == lab_id))
        db.commit()


def _categoria() -> str:
    with SessionLocal() as db:
        cat = db.scalar(select(LabCategoria).where(LabCategoria.activa.is_(True)))
        assert cat is not None
        return cat.nombre


def _atencion(lab_id: int, uid: int, auxiliar: str, desc: str):
    return client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab_id,
            "categoria": _categoria(),
            "descripcion": f"{MARK}{desc}",
            "solucion": "reinicio",
            "auxiliar_nombre": auxiliar,
        },
        headers=h(uid),
    )


def test_atencion_auxiliar_vinculado_firma_con_su_nombre(nomina, usuarios, lab):
    uid = usuarios("ana")
    assert _vincular(f"{AUX}Ana", uid).status_code == 200
    # intenta firmar como Beto: se fuerza Ana; el extra se mantiene
    r = _atencion(lab, uid, f"{AUX}Beto + {AUX}Ceci", "a1")
    assert r.status_code == 200, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana + {AUX}Ceci"
    # sin nombre: igual firma Ana
    r = _atencion(lab, uid, "", "a2")
    assert r.status_code == 200, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana"
    # el extra sigue validándose por nombre
    assert _atencion(lab, uid, f"{AUX}Ana + Nadie", "a3").status_code == 400
    # el propio nombre como extra no se duplica
    r = _atencion(lab, uid, f"{AUX}Beto + {AUX}Ana", "a4")
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana"


def test_atencion_auxiliar_sin_vinculo_rechazada(nomina, usuarios, lab):
    uid = usuarios("ana")
    r = _atencion(lab, uid, f"{AUX}Ana", "s1")
    assert r.status_code == 403
    assert SIN_VINCULO in r.json()["detail"]


def test_atencion_tecnico_y_jefe_sin_cambios(nomina, lab):
    r = _atencion(lab, UID_TEC, f"{AUX}Beto + {AUX}Ceci", "t1")
    assert r.status_code == 200, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Beto + {AUX}Ceci"
    r = _atencion(lab, UID_JEFE, f"{AUX}Ana", "j1")
    assert r.status_code == 200, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana"


def _pc_con_software(lab_id: int) -> tuple[int, int]:
    r = client.post(
        "/api/software", json={"nombre": f"{MARK}Office"}, headers=h(UID_JEFE)
    )
    assert r.status_code in (200, 201), r.text
    sw_id = r.json()["id"]
    r = client.put(
        f"/api/software/laboratorios/{lab_id}",
        json={"software_ids": [sw_id]},
        headers=h(UID_JEFE),
    )
    assert r.status_code in (200, 204), r.text
    with SessionLocal() as db:
        pc = LabPc(
            laboratorio_id=lab_id,
            nombre=f"{MARK}PC1",
            fila=0,
            col=0,
            activa=True,
            created_at=datetime.now(UTC),
        )
        db.add(pc)
        db.commit()
        db.refresh(pc)
        return pc.id, sw_id


def test_software_marcar_estado_por_cuenta(nomina, usuarios, lab):
    pc_id, sw_id = _pc_con_software(lab)
    body = {"software_id": sw_id, "estado": "dañado", "auxiliar_nombre": f"{AUX}Beto"}
    uid = usuarios("ana")
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(uid))
    assert r.status_code == 403
    assert SIN_VINCULO in r.json()["detail"]
    assert _vincular(f"{AUX}Ana", uid).status_code == 200
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(uid))
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        fila = db.scalar(
            select(LabAtencion).where(
                LabAtencion.laboratorio_id == lab, LabAtencion.usuario_id == uid
            )
        )
        assert fila is not None and fila.auxiliar_nombre == f"{AUX}Ana"
    # Técnico sigue firmando con el nombre enviado
    body["estado"] = "instalado"
    r = client.put(f"/api/software/pcs/{pc_id}", json=body, headers=h(UID_TEC))
    assert r.status_code == 200, r.text


def _png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (0, 255, 0)).save(buf, "PNG")
    return buf.getvalue()


def test_novedades_por_cuenta(nomina, usuarios):
    uid = usuarios("ana")
    data = {"tipo": "novedad", "texto": "proyector", "auxiliar_nombre": f"{AUX}Beto"}
    r = client.post("/api/novedades", data=data, headers=h(uid))
    assert r.status_code == 403
    assert SIN_VINCULO in r.json()["detail"]
    assert _vincular(f"{AUX}Ana", uid).status_code == 200
    r = client.post("/api/novedades", data=data, headers=h(uid))
    assert r.status_code == 201, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana"
    # sin nombre también vale: lo pone la cuenta
    r = client.post(
        "/api/novedades", data={"tipo": "novedad", "texto": "x"}, headers=h(uid)
    )
    assert r.status_code == 201, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Ana"
    # Técnico sin cambios
    r = client.post("/api/novedades", data=data, headers=h(UID_TEC))
    assert r.status_code == 201, r.text
    assert r.json()["auxiliar_nombre"] == f"{AUX}Beto"
    with SessionLocal() as db:
        db.execute(delete(Novedad).where(Novedad.id == r.json()["id"]))
        db.commit()


def test_devolver_objeto_por_cuenta(nomina, usuarios):
    ana = usuarios("ana")
    beto = usuarios("beto")
    assert _vincular(f"{AUX}Ana", ana).status_code == 200
    assert _vincular(f"{AUX}Beto", beto).status_code == 200
    r = client.post(
        "/api/novedades",
        data={"tipo": "objeto", "texto": "llavero"},
        files={"foto": ("o.png", _png(), "image/png")},
        headers=h(ana),
    )
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    try:
        # Beto dice ser Ana: no le alcanza, su cuenta es Beto
        r = client.patch(
            f"/api/novedades/{nid}",
            json={
                "accion": "devolver",
                "entregado_a": "x",
                "auxiliar_nombre": f"{AUX}Ana",
            },
            headers=h(beto),
        )
        assert r.status_code == 400, r.text
        # Ana devuelve sin mandar nombre: lo pone la cuenta
        r = client.patch(
            f"/api/novedades/{nid}",
            json={"accion": "devolver", "entregado_a": "dueño"},
            headers=h(ana),
        )
        assert r.status_code == 200, r.text
        assert r.json()["estado"] == "devuelto"
    finally:
        with SessionLocal() as db:
            fila = db.get(Novedad, nid)
            if fila is not None and fila.foto_path:
                (DATA_DIR / "aux_reportes" / fila.foto_path).unlink(missing_ok=True)
