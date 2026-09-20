"""Tests S3 contra postgres-dev real. Filas marcadas TEST-S3 bajo usuario 1, con limpieza."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

UID_MATTIAS = 1
UID_DIEGO = 2
UID_JEFE = 8
MARK = "TEST-S3-"

client = TestClient(app)


EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
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
        client.get(
            "/api/atenciones", headers={"Authorization": "Bearer invalido"}
        ).status_code
        == 401
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
    arbol = client.get("/api/jerarquia/arbol", headers=h(UID_JEFE)).json()
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
    hoy = datetime.now(UTC).date().isoformat()
    assert any(
        a["descripcion"] == f"{MARK}a" and a["fecha_registro"] == hoy for a in todas
    )


def test_stats_por_medio(filas_prueba):
    s = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    assert len(s["por_medio"]) > 0
    assert all(set(m) == {"medio", "total"} for m in s["por_medio"])
    assert sum(m["total"] for m in s["por_medio"]) == s["total"]


def test_stats_categoria_mes(filas_prueba):
    s = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    assert len(s["por_categoria_mes"]) > 0
    assert all(
        set(c) == {"categoria", "anio", "mes", "total"} for c in s["por_categoria_mes"]
    )
    assert sum(c["total"] for c in s["por_categoria_mes"]) == s["total"]


def test_stats_filtro_jerarquia(filas_prueba):
    sin_filtro = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    arbol = client.get("/api/jerarquia/arbol", headers=h(UID_JEFE)).json()
    padre = next(p for p in arbol["padres"] if p["id"] == 1)
    con_padre = client.get(
        "/api/atenciones/stats",
        params={"grupo_padre_id": padre["id"]},
        headers=h(UID_JEFE),
    ).json()
    assert 0 < con_padre["total"] < sin_filtro["total"]
    assert sum(c["total"] for c in con_padre["por_categoria"]) == con_padre["total"]

    areas = [
        a
        for a in arbol["areas"]
        if a["grupo_padre_id"] == padre["id"] and a["grupo_id"]
    ]
    if areas:
        area = areas[0]
        con_area = client.get(
            "/api/atenciones/stats",
            params={"area_id": area["id"]},
            headers=h(UID_JEFE),
        ).json()
        assert con_area["total"] <= con_padre["total"]
        assert sum(c["total"] for c in con_area["por_categoria"]) == con_area["total"]
        con_grupo = client.get(
            "/api/atenciones/stats",
            params={"grupo_id": area["grupo_id"]},
            headers=h(UID_JEFE),
        ).json()
        assert con_area["total"] <= con_grupo["total"] <= con_padre["total"]


def test_stats_filtro_sin_resultados(filas_prueba):
    s = client.get(
        "/api/atenciones/stats", params={"area_id": 999999}, headers=h(UID_JEFE)
    ).json()
    assert s["total"] == 0
    assert s["por_categoria"] == []
    assert s["por_medio"] == []
    assert s["por_categoria_mes"] == []
    assert s["por_dia"] == []
    assert s["por_tipo_solicitante"] == []
    assert s["por_padre"] == []
    assert s["por_grupo"] == []
    assert s["flujo_sankey"] == []
    assert s["por_tecnico_fuera"] == []


def test_stats_agregados_nuevos(filas_prueba):
    s = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    assert len(s["por_tipo_solicitante"]) > 0
    assert all(set(t) == {"tipo", "total"} for t in s["por_tipo_solicitante"])

    assert len(s["por_padre"]) > 0
    assert 0 < sum(p["total"] for p in s["por_padre"]) <= s["total"]
    assert all(p["total"] > 0 for p in s["por_grupo"])
    assert all(a["nombre"] for a in s["por_area_id"])

    assert len(s["por_dia"]) > 0
    assert all(set(d) == {"fecha", "total"} for d in s["por_dia"])
    assert sum(d["total"] for d in s["por_dia"]) == s["total"]

    assert len(s["flujo_sankey"]) > 0
    assert all(
        set(f) == {"medio", "categoria", "grupo_padre", "total"}
        for f in s["flujo_sankey"]
    )
    assert all(f["grupo_padre"] for f in s["flujo_sankey"])

    assert len(s["por_tecnico_fuera"]) > 0
    assert all(
        set(t) == {"usuario_id", "display_name", "total", "fuera"}
        for t in s["por_tecnico_fuera"]
    )
    assert all(t["fuera"] <= t["total"] for t in s["por_tecnico_fuera"])

    assert len(s["por_tecnico_categoria"]) > 0
    assert all(
        set(t) == {"usuario_id", "display_name", "categoria", "total"}
        for t in s["por_tecnico_categoria"]
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
        "por_medio",
        "por_categoria_mes",
        "por_tipo_solicitante",
        "por_padre",
        "por_grupo",
        "por_area_id",
        "por_dia",
        "flujo_sankey",
        "por_tecnico_fuera",
        "por_tecnico_categoria",
        "asistencias",
    }
    assert antes["total"] >= 2
    assert any(t["usuario_id"] == UID_MATTIAS for t in antes["por_tecnico"])


def test_put_sync_y_permisos(filas_prueba):
    target = filas_prueba[0]
    arbol = client.get("/api/jerarquia/arbol", headers=h(UID_MATTIAS)).json()
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
            headers=h(UID_JEFE),
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
        client.delete(f"/api/atenciones/{target}", headers=h(UID_JEFE)).status_code
        == 403
    )
    assert (
        client.delete(f"/api/atenciones/{target}", headers=h(UID_MATTIAS)).status_code
        == 204
    )
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    assert target not in [a["id"] for a in todas]
    filas_prueba.remove(target)


def test_put_fecha_y_colaborador(filas_prueba):
    target = filas_prueba[0]
    colegas = client.get("/api/usuarios", headers=h(UID_JEFE)).json()
    colab = next(u for u in colegas if u["id"] == UID_DIEGO)
    assert (
        client.put(
            f"/api/atenciones/{target}",
            json={"fecha_registro": "2026-01-15", "colaborador_id": colab["id"]},
            headers=h(UID_MATTIAS),
        ).status_code
        == 204
    )
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    editada = next(a for a in todas if a["id"] == target)
    assert editada["fecha_registro"] == "2026-01-15"
    assert editada["colaborador_id"] == colab["id"]
    assert editada["colaborador_nombre"] == colab["display_name"]
    assert (
        client.put(
            f"/api/atenciones/{target}",
            json={"colaborador_id": 999999},
            headers=h(UID_MATTIAS),
        ).status_code
        == 400
    )
