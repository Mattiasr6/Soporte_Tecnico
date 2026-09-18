"""Tests S3 contra postgres-dev real. Filas marcadas TEST-S3 bajo usuario 1, con limpieza."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app

UID_MATTIAS = 1
UID_DIEGO = 2
UID_JEFE = 8
MARK = "TEST-S3-"

client = TestClient(app)


def h(uid: int) -> dict[str, str]:
    return {"X-User-Id": str(uid)}


def _base_item(descripcion: str) -> dict[str, object]:
    return {
        "area_solicitante": "Administrativos",
        "medio_solicitud": "Interno",
        "usuario_solicitante": "ADM",
        "categoria": "Hardware",
        "descripcion": descripcion,
        "solucion": "Reinicio",
    }


@pytest.fixture
def filas_prueba():
    r = client.post(
        "/api/atenciones/batch",
        json={"atenciones": [_base_item(f"{MARK}a"), _base_item(f"{MARK}b")]},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"registros_insertados": 2}
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    ids = [a["id"] for a in todas if a["descripcion"].startswith(MARK)]
    assert len(ids) == 2
    yield ids
    for i in ids:
        client.delete(f"/api/atenciones/{i}", headers=h(UID_MATTIAS))
    resto = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    assert not [a for a in resto if a["descripcion"].startswith(MARK)]


def test_auth_requerida():
    assert client.get("/api/atenciones").status_code == 401
    assert client.get("/api/atenciones/stats", headers=h(UID_DIEGO)).status_code == 401
    assert (
        client.get("/api/atenciones", headers={"X-User-Id": "999"}).status_code == 401
    )


def test_tecnico_solo_lo_propio():
    r = client.post(
        "/api/atenciones/batch",
        json={"atenciones": [_base_item(f"{MARK}solo")]},
        headers=h(UID_DIEGO),
    )
    assert r.status_code == 200
    try:
        rows = client.get("/api/atenciones", headers=h(UID_DIEGO)).json()
        assert len(rows) > 0
        assert all(a["usuario_id"] == UID_DIEGO for a in rows)
    finally:
        todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
        for a in todas:
            if a["descripcion"] == f"{MARK}solo":
                client.delete(f"/api/atenciones/{a['id']}", headers=h(UID_DIEGO))


def test_jefe_filtra(filas_prueba):
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    propias = client.get(
        "/api/atenciones", params={"usuario_id": UID_MATTIAS}, headers=h(UID_JEFE)
    ).json()
    assert len(todas) >= len(propias) > 0
    assert all(a["usuario_id"] == UID_MATTIAS for a in propias)
    assert any(a["id"] in filas_prueba for a in propias)


def test_batch_validaciones():
    assert (
        client.post(
            "/api/atenciones/batch", json={"atenciones": []}, headers=h(UID_MATTIAS)
        ).status_code
        == 400
    )
    mala = _base_item(f"{MARK}x")
    mala["categoria"] = "NoExiste"
    r = client.post(
        "/api/atenciones/batch",
        json={"atenciones": [mala]},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 400
    assert "NoExiste" in r.json()["detail"]
    fk_mala = _base_item(f"{MARK}y")
    fk_mala["area_id"] = 999999
    assert (
        client.post(
            "/api/atenciones/batch",
            json={"atenciones": [fk_mala]},
            headers=h(UID_MATTIAS),
        ).status_code
        == 400
    )


def test_batch_legacy_y_fk(filas_prueba):
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    legacy = next(a for a in todas if a["descripcion"] == f"{MARK}a")
    assert legacy["grupo_padre_id"] == 1  # Administrativos mapeado por nombre
    assert legacy["area_solicitante"] == "Administrativos"
    arbol = client.get("/api/jerarquia/arbol").json()
    area = arbol["areas"][0]
    r = client.post(
        "/api/atenciones/batch",
        json={
            "atenciones": [
                {
                    **_base_item(f"{MARK}fk"),
                    "area_id": area["id"],
                    "area_solicitante": "",
                }
            ]
        },
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200
    try:
        todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
        creada = next(a for a in todas if a["descripcion"] == f"{MARK}fk")
        assert creada["area_id"] == area["id"]
        assert creada["area_solicitante"] == area["nombre"]
        assert creada["grupo_padre_id"] == area["grupo_padre_id"]
        assert isinstance(creada["fuera_de_turno"], bool)
    finally:
        todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
        for a in todas:
            if a["descripcion"] == f"{MARK}fk":
                client.delete(f"/api/atenciones/{a['id']}", headers=h(UID_MATTIAS))


def test_fecha_default_hoy(filas_prueba):
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    hoy = datetime.now(timezone.utc).date().isoformat()
    assert any(
        a["descripcion"] == f"{MARK}a" and a["fecha_registro"] == hoy for a in todas
    )


def test_stats_delta(filas_prueba):
    antes = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    assert set(antes) == {
        "total",
        "fuera_de_turno",
        "por_tecnico",
        "por_categoria",
        "por_mes",
        "por_area",
        "asistencias",
    }
    assert antes["total"] >= 2
    assert any(t["usuario_id"] == UID_MATTIAS for t in antes["por_tecnico"])


def test_put_sync_y_permisos(filas_prueba):
    target = filas_prueba[0]
    arbol = client.get("/api/jerarquia/arbol").json()
    area = arbol["areas"][0]
    assert (
        client.put(
            f"/api/atenciones/{target}",
            json={"area_id": area["id"]},
            headers=h(UID_DIEGO),
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/atenciones/{target}",
            json={"area_id": area["id"]},
            headers=h(UID_MATTIAS),
        ).status_code
        == 204
    )
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    editada = next(a for a in todas if a["id"] == target)
    assert editada["area_id"] == area["id"]
    assert editada["area_solicitante"] == area["nombre"]


def test_delete_permiso_y_borrado(filas_prueba):
    target = filas_prueba[1]
    assert (
        client.delete(f"/api/atenciones/{target}", headers=h(UID_DIEGO)).status_code
        == 403
    )
    assert (
        client.delete(f"/api/atenciones/{target}", headers=h(UID_MATTIAS)).status_code
        == 204
    )
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    assert target not in [a["id"] for a in todas]
    filas_prueba.remove(target)
