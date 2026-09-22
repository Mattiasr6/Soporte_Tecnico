"""Tests de la administración del catálogo y su propagación, contra postgres-dev real.

Crea un par de sectores, una dependencia y un área marcados TEST-ADMIN, y los borra al final.
La parte crítica es que mover un nodo re-apunte las atenciones (los 3 FK van copiados).
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

UID_MATTIAS = 1
UID_PAUL = 3
UID_JEFE = 8

MARK = "TEST-ADMIN "

client = TestClient(app)
EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
    3: "paul.quispe@upds.edu.bo",
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


def _atencion(area_id: int, marca: str) -> dict[str, object]:
    return {
        "area_id": area_id,
        "medio_solicitud": "Interno",
        "usuario_solicitante": "ADM",
        "categoria": "Hardware",
        "descripcion": f"{MARK}{marca}",
        "solucion": "Reinicio",
    }


def _crear(area_id: int, marca: str) -> int:
    r = client.post(
        "/api/atenciones/batch",
        json={"atenciones": [_atencion(area_id, marca)]},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200, r.text
    filas = client.get(
        "/api/atenciones", headers=h(UID_JEFE), params={"limit": 2000}
    ).json()
    ids = [a["id"] for a in filas if a["descripcion"] == f"{MARK}{marca}"]
    assert len(ids) == 1, f"no se encontro la atencion {marca}"
    return ids[0]


def _atencion_por_id(uid: int) -> dict[str, object]:
    filas = client.get(
        "/api/atenciones", headers=h(UID_JEFE), params={"limit": 2000}
    ).json()
    return next(a for a in filas if a["id"] == uid)


@pytest.fixture
def catalogo():
    s1 = client.post(
        "/api/jerarquia/grupos-padres",
        json={"nombre": MARK + "Sector"},
        headers=h(UID_MATTIAS),
    )
    assert s1.status_code == 201, s1.text
    s2 = client.post(
        "/api/jerarquia/grupos-padres",
        json={"nombre": MARK + "Sector Dos"},
        headers=h(UID_MATTIAS),
    )
    assert s2.status_code == 201, s2.text
    dep = client.post(
        "/api/jerarquia/grupos",
        json={"nombre": MARK + "Dep", "grupo_padre_id": s1.json()["id"]},
        headers=h(UID_MATTIAS),
    )
    assert dep.status_code == 201, dep.text
    area = client.post(
        "/api/jerarquia/areas",
        json={
            "nombre": MARK + "Area",
            "grupo_padre_id": s1.json()["id"],
            "grupo_id": dep.json()["id"],
        },
        headers=h(UID_MATTIAS),
    )
    assert area.status_code == 201, area.text
    creadas = [s1.json()["id"], s2.json()["id"], dep.json()["id"], area.json()["id"]]

    yield {
        "sector": s1.json()["id"],
        "sector2": s2.json()["id"],
        "dep": dep.json()["id"],
        "area": area.json()["id"],
        "sector_json": s1.json(),
        "dep_json": dep.json(),
        "area_json": area.json(),
    }

    for a in client.get(
        "/api/atenciones", headers=h(UID_JEFE), params={"limit": 2000}
    ).json():
        if a.get("area_id") == creadas[3]:
            client.delete(f"/api/atenciones/{a['id']}", headers=h(UID_MATTIAS))
    client.delete(f"/api/jerarquia/areas/{creadas[3]}", headers=h(UID_MATTIAS))
    client.delete(f"/api/jerarquia/grupos/{creadas[2]}", headers=h(UID_MATTIAS))
    client.delete(f"/api/jerarquia/grupos-padres/{creadas[0]}", headers=h(UID_MATTIAS))
    client.delete(f"/api/jerarquia/grupos-padres/{creadas[1]}", headers=h(UID_MATTIAS))


def test_solo_privilegiados_escriben():
    r = client.post(
        "/api/jerarquia/grupos-padres", json={"nombre": "X"}, headers=h(UID_PAUL)
    )
    assert r.status_code == 403
    assert (
        client.put(
            "/api/jerarquia/areas/1", json={"nombre": "X"}, headers=h(UID_PAUL)
        ).status_code
        == 403
    )
    assert (
        client.delete("/api/jerarquia/areas/1", headers=h(UID_PAUL)).status_code == 403
    )


def test_codigo_autogenerado(catalogo):
    assert catalogo["sector_json"]["codigo"] == "test-admin-sector"
    assert catalogo["dep_json"]["codigo"] == "test-admin-dep"
    assert catalogo["area_json"]["codigo"] == "test-admin-area"


def test_colisiones_de_nombre_y_codigo(catalogo):
    repetido = client.post(
        "/api/jerarquia/grupos-padres",
        json={"nombre": MARK + "Sector"},
        headers=h(UID_MATTIAS),
    )
    assert repetido.status_code == 400
    assert "Ya existe" in repetido.json()["detail"]

    area_repetida = client.post(
        "/api/jerarquia/areas",
        json={
            "nombre": MARK + "Area",
            "grupo_padre_id": catalogo["sector"],
            "grupo_id": catalogo["dep"],
        },
        headers=h(UID_MATTIAS),
    )
    assert area_repetida.status_code == 400

    codigo_ocupado = client.post(
        "/api/jerarquia/areas",
        json={
            "nombre": MARK + "Otra",
            "grupo_padre_id": catalogo["sector"],
            "codigo": catalogo["area_json"]["codigo"],
        },
        headers=h(UID_MATTIAS),
    )
    assert codigo_ocupado.status_code == 400
    assert "ya está en uso" in codigo_ocupado.json()["detail"]


def test_area_no_acepta_dependencia_de_otro_sector(catalogo):
    r = client.post(
        "/api/jerarquia/areas",
        json={
            "nombre": MARK + "Cruzada",
            "grupo_padre_id": catalogo["sector2"],
            "grupo_id": catalogo["dep"],
        },
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 400
    assert "otro sector" in r.json()["detail"]


def test_mover_area_propaga_a_las_atenciones(catalogo):
    atencion_id = _crear(catalogo["area"], "mover-area")
    antes = _atencion_por_id(atencion_id)
    assert antes["grupo_padre_id"] == catalogo["sector"]
    assert antes["grupo_id"] == catalogo["dep"]

    r = client.put(
        f"/api/jerarquia/areas/{catalogo['area']}",
        json={"grupo_padre_id": catalogo["sector2"], "grupo_id": None},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200, r.text
    tras = _atencion_por_id(atencion_id)
    assert tras["grupo_padre_id"] == catalogo["sector2"]
    assert tras["grupo_id"] is None


def test_mover_dependencia_arrastra_sus_areas(catalogo):
    atencion_id = _crear(catalogo["area"], "mover-dep")

    r = client.put(
        f"/api/jerarquia/grupos/{catalogo['dep']}",
        json={"grupo_padre_id": catalogo["sector2"]},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200, r.text

    arbol = client.get(
        "/api/jerarquia/arbol",
        params={"incluir_inactivas": True},
        headers=h(UID_JEFE),
    ).json()
    area = next(a for a in arbol["areas"] if a["id"] == catalogo["area"])
    assert area["grupo_padre_id"] == catalogo["sector2"]
    assert _atencion_por_id(atencion_id)["grupo_padre_id"] == catalogo["sector2"]


def test_no_se_borra_con_hijos_ni_atenciones(catalogo):
    assert (
        client.delete(
            f"/api/jerarquia/grupos-padres/{catalogo['sector']}",
            headers=h(UID_MATTIAS),
        ).status_code
        == 400
    )
    assert (
        client.delete(
            f"/api/jerarquia/grupos/{catalogo['dep']}", headers=h(UID_MATTIAS)
        ).status_code
        == 400
    )

    atencion_id = _crear(catalogo["area"], "borrar-area")
    r = client.delete(
        f"/api/jerarquia/areas/{catalogo['area']}", headers=h(UID_MATTIAS)
    )
    assert r.status_code == 400
    assert "no se puede borrar" in r.json()["detail"]

    client.delete(f"/api/atenciones/{atencion_id}", headers=h(UID_MATTIAS))
    assert (
        client.delete(
            f"/api/jerarquia/areas/{catalogo['area']}", headers=h(UID_MATTIAS)
        ).status_code
        == 204
    )


def test_desactivar_area_la_esconde_del_selector(catalogo):
    r = client.put(
        f"/api/jerarquia/areas/{catalogo['area']}",
        json={"activo": False},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200
    assert r.json()["activo"] is False

    activas = client.get("/api/jerarquia/arbol", headers=h(UID_JEFE)).json()["areas"]
    assert all(a["id"] != catalogo["area"] for a in activas)

    todas = client.get(
        "/api/jerarquia/arbol",
        params={"incluir_inactivas": True},
        headers=h(UID_JEFE),
    ).json()["areas"]
    assert any(a["id"] == catalogo["area"] for a in todas)


def test_renombrar_actualiza_el_texto_legado(catalogo):
    atencion_id = _crear(catalogo["area"], "renombrar")
    nuevo = MARK + "Area Renombrada"

    r = client.put(
        f"/api/jerarquia/areas/{catalogo['area']}",
        json={"nombre": nuevo, "actualizar_texto_legado": True},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 200, r.text
    assert r.json()["codigo"] == "test-admin-area"
    assert r.json()["nombre"] == nuevo
    assert _atencion_por_id(atencion_id)["area_solicitante"] == nuevo


def test_patch_jerarquia_solo_jefes(catalogo):
    atencion_id = _crear(catalogo["area"], "patch")

    assert (
        client.patch(
            f"/api/atenciones/{atencion_id}/jerarquia",
            json={"area_id": catalogo["area"]},
            headers=h(UID_PAUL),
        ).status_code
        == 403
    )

    r = client.patch(
        f"/api/atenciones/{atencion_id}/jerarquia",
        json={"area_id": catalogo["area"]},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 204, r.text
    tras = _atencion_por_id(atencion_id)
    assert tras["area_id"] == catalogo["area"]
    assert tras["grupo_padre_id"] == catalogo["sector"]
    assert tras["grupo_id"] == catalogo["dep"]
