"""Tests de Novedades: muro de turno (novedades, objetos, cierres con foto)."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.base import SessionLocal
from app.main import app
from app.models.novedad import Novedad
from app.models.usuario import Usuario  # noqa: F401  (registra el modelo)

client = TestClient(app)

UID_TEC = 2
UID_JEFE = 8
EMAILS = {
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}

MARK = "TEST-NOV-"


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


FOTOS_DIR = Path(__file__).resolve().parent.parent / "data" / "aux_reportes"


def _fotos_antes() -> set[Path]:
    if not FOTOS_DIR.exists():
        return set()
    return {p for p in FOTOS_DIR.rglob("*") if p.is_file()}


@pytest.fixture
def limpio():
    fotos = _fotos_antes()
    yield
    with SessionLocal() as db:
        for fila in db.scalars(
            select(Novedad).where(Novedad.auxiliar_nombre.like(f"{MARK}%"))
        ).all():
            db.delete(fila)
        db.commit()
    for p in _fotos_antes() - fotos:
        p.unlink(missing_ok=True)


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _crear(tipo: str, texto: str, foto: bool = False, **extra: object) -> dict:
    data = {"tipo": tipo, "texto": texto, "auxiliar_nombre": f"{MARK}1"}
    data.update(extra)
    files = {"foto": ("llaves.png", PNG, "image/png")} if foto else None
    r = client.post("/api/novedades", data=data, files=files, headers=h(UID_TEC))
    assert r.status_code == 201, r.text
    assert isinstance(r.json(), dict)
    return r.json()


def test_crear_y_listar(limpio):
    n = _crear("novedad", f"{MARK} turno tranquilo")
    assert n["estado"] == "publicado"
    assert n["tiene_foto"] is False
    r = client.get("/api/novedades", params={"tipo": "novedad"}, headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    assert any(f["id"] == n["id"] for f in r.json())
    assert (
        client.get(
            "/api/novedades", params={"tipo": "cuchara"}, headers=h(UID_TEC)
        ).status_code
        == 400
    )


def test_objeto_se_devuelve(limpio):
    n = _crear("objeto", f"{MARK} cargador olvidado lab 8")
    assert n["estado"] == "pendiente"
    r = client.patch(
        f"/api/novedades/{n['id']}",
        json={"accion": "devolver", "auxiliar_nombre": "Otro Nombre"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 400, r.text
    r = client.patch(
        f"/api/novedades/{n['id']}",
        json={"accion": "devolver", "auxiliar_nombre": f"{MARK}1"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "devuelto"


def test_cierre_exige_foto_y_validacion(limpio):
    r = client.post(
        "/api/novedades",
        data={"tipo": "cierre", "texto": "x", "auxiliar_nombre": f"{MARK}1"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 400
    n = _crear("cierre", f"{MARK} llaves en su lugar", foto=True)
    assert n["estado"] == "pendiente"
    assert n["tiene_foto"] is True
    r = client.get(f"/api/novedades/{n['id']}/foto", headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    assert r.content.startswith(PNG[:8])
    r = client.patch(
        f"/api/novedades/{n['id']}", json={"accion": "validar"}, headers=h(UID_TEC)
    )
    assert r.status_code == 403, r.text
    r = client.patch(
        f"/api/novedades/{n['id']}", json={"accion": "validar"}, headers=h(UID_JEFE)
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "validado"


def test_vencido_y_purga(limpio):
    with SessionLocal() as db:
        db.add(
            Novedad(
                usuario_id=UID_TEC,
                auxiliar_nombre=f"{MARK}viejo",
                tipo="objeto",
                texto="mouse olvidado",
                turno=None,
                laboratorio_id=None,
                foto_path=None,
                estado="pendiente",
                fecha_registro=(datetime.now(UTC) - timedelta(days=100)).date(),
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    r = client.get(
        "/api/novedades", params={"estado": "vencido"}, headers=h(UID_TEC)
    )
    assert r.status_code == 200, r.text
    assert any(f["auxiliar_nombre"] == f"{MARK}viejo" for f in r.json())
    r = client.post("/api/novedades/purga", headers=h(UID_TEC))
    assert r.status_code == 403
    r = client.post("/api/novedades/purga", headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    assert r.json()["eliminados"] >= 1
    with SessionLocal() as db:
        queda = db.scalars(
            select(Novedad).where(Novedad.auxiliar_nombre == f"{MARK}viejo")
        ).first()
        assert queda is None


def test_rechazos(limpio):
    assert (
        client.post(
            "/api/novedades",
            data={"tipo": "objeto", "texto": "", "auxiliar_nombre": f"{MARK}1"},
            files={"foto": ("x.png", PNG, "image/png")},
            headers=h(UID_TEC),
        ).status_code
        == 400
    )
    assert client.get("/api/novedades/999999/foto", headers=h(UID_TEC)).status_code in (
        404,
        422,
    )
    with SessionLocal() as db:
        db.execute(delete(Novedad).where(Novedad.auxiliar_nombre.like(f"{MARK}%")))
        db.commit()
