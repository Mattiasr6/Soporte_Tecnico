import os

from fastapi.testclient import TestClient

from app.main import app


def _token() -> str:
    r = TestClient(app).post(
        "/api/auth/login",
        json={
            "email": "mattias.ribera@upds.edu.bo",
            "password": os.environ["SEED_PASSWORD"],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


client = TestClient(app, headers={"Authorization": f"Bearer {_token()}"})


def test_grupos_padres_orden():
    r = client.get("/api/jerarquia/grupos-padres")
    assert r.status_code == 200
    nombres = [p["nombre"] for p in r.json()]
    assert nombres == ["Administrativos", "Académicos", "Extras"]


def test_arbol_forma_y_conteos():
    r = client.get("/api/jerarquia/arbol")
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"padres", "grupos", "areas"}
    assert len(data["padres"]) == 3
    assert len(data["areas"]) > 0
    assert all(a["activo"] for a in data["areas"])
    nombres = [a["nombre"] for a in data["areas"]]
    assert nombres == sorted(nombres)
    assert set(data["areas"][0]) == {
        "id",
        "grupo_padre_id",
        "grupo_id",
        "nombre",
        "codigo",
        "activo",
    }


def test_filtros_coherentes():
    todo = client.get("/api/jerarquia/grupos").json()
    filtrado = client.get("/api/jerarquia/grupos", params={"grupo_padre_id": 1}).json()
    assert 0 < len(filtrado) <= len(todo)
    assert all(g["grupo_padre_id"] == 1 for g in filtrado)
    gid = filtrado[0]["id"]
    areas = client.get("/api/jerarquia/areas", params={"grupo_id": gid}).json()
    assert all(a["grupo_id"] == gid for a in areas)


def test_areas_legacy_contiene_extras():
    r = client.get("/api/areas")
    assert r.status_code == 200
    areas = r.json()
    assert "Aula B-02" in areas
    assert "Plaza UPDS" in areas
    assert areas == sorted(areas)
