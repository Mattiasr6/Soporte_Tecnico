"""Tests S4 contra postgres-dev real. Filas marcadas TEST-S4, con limpieza."""

import os
from datetime import datetime, timezone

from app.main import app
from app.services.csv_import import detectar_encoding, parse_csv
from fastapi.testclient import TestClient

UID_MATTIAS = 1
UID_JEFE = 8
MARK = "TEST-S4-"

client = TestClient(app)


EMAILS = {
    1: "mattias.ribera@upds.edu.bo",
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


def _csv_linea(
    num: int,
    fecha: str,
    area: str,
    solicitante: str,
    medio: str,
    categoria: str,
    descripcion: str,
    solucion: str,
) -> str:
    return f"{num};{fecha};{area};{solicitante};{medio};{categoria};{descripcion};{solucion}"


HEADER = "id;fecha;area;solicitante;medio;categoria;descripcion;solucion;obs;enlace"


def _limpiar():
    todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    for a in todas:
        if a["descripcion"].startswith(MARK):
            client.delete(f"/api/atenciones/{a['id']}", headers=h(UID_MATTIAS))


def test_detectar_encoding():
    assert detectar_encoding(b"\xef\xbb\xbfhola") == "utf-8-sig"
    assert detectar_encoding(b"\xff\xfeh\x00") == "utf-16-le"
    assert detectar_encoding("ñandú".encode("latin-1")) == "latin-1"


def test_parse_puro_sin_db():
    contenido = "\n".join(
        [
            HEADER,
            _csv_linea(
                1,
                "18/09/2026",
                "Biblioteca",
                "ADM",
                "Interno",
                "impresion",
                f"{MARK}x",
                "Fix",
            ),
            _csv_linea(2, "mala", "X", "ZZZ", "Paloma", "Rara", f"{MARK}y", "Fix"),
            "corta",
            "no-num;18/09/2026;A;ADM;Interno;Otros;D;S",
            _csv_linea(
                3, "18/09/2026", "", "ADM", "Interno", "Otros", f"{MARK}z", "Fix"
            ),
        ]
    ).encode("latin-1")
    filas, errores = parse_csv(contenido)
    assert len(filas) == 2
    assert filas[0].categoria == "Impresión"
    assert filas[1].categoria == "Otros"
    assert filas[1].medio == "Interno"
    assert filas[1].usuario_solicitante == "ADM"
    assert filas[1].fecha == datetime.now(timezone.utc).date()
    assert len(errores) == 2  # categoría rara + campos faltantes


def test_import_latin1_con_tildes():
    area = client.get("/api/jerarquia/areas", headers=h(UID_MATTIAS)).json()[0][
        "nombre"
    ]
    contenido = "\n".join(
        [
            HEADER,
            _csv_linea(
                1,
                "18/09/2026",
                area,
                "DOC",
                "WhatsApp",
                "Software",
                f"{MARK}ñandú",
                "Solución tú",
            ),
            _csv_linea(
                2,
                "18/09/2026",
                "Inexistente Zzz",
                "ADM",
                "Interno",
                "Otros",
                f"{MARK}b",
                "S",
            ),
        ]
    ).encode("latin-1")
    try:
        r = client.post(
            "/api/atenciones/import-csv",
            files={"file": ("carga.csv", contenido, "text/csv")},
            headers=h(UID_MATTIAS),
        )
        assert r.status_code == 200, r.text
        assert r.json()["registros_insertados"] == 2
        todas = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
        reales = [a for a in todas if a["descripcion"].startswith(MARK)]
        con_area = next(a for a in reales if a["area_solicitante"] == area)
        assert con_area["area_id"] is not None  # jerarquía resuelta
        sin_area = next(a for a in reales if a["area_solicitante"] == "Inexistente Zzz")
        assert sin_area["area_id"] is None  # legacy sin FK, igual se inserta
        assert "ñandú" in con_area["descripcion"]
    finally:
        _limpiar()
    resto = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    assert not [a for a in resto if a["descripcion"].startswith(MARK)]


def test_import_todo_malo_400():
    contenido = "\n".join(
        [
            HEADER,
            _csv_linea(1, "18/09/2026", "", "ADM", "Interno", "Otros", f"{MARK}z", "S"),
        ]
    ).encode()
    r = client.post(
        "/api/atenciones/import-csv",
        files={"file": ("todo.csv", contenido, "text/csv")},
        headers=h(UID_MATTIAS),
    )
    assert r.status_code == 400


def test_import_archivo_invalido():
    assert (
        client.post(
            "/api/atenciones/import-csv",
            files={"file": ("x.txt", b"a;b", "text/plain")},
            headers=h(UID_MATTIAS),
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/atenciones/import-csv",
            files={"file": ("vacio.csv", b"", "text/csv")},
            headers=h(UID_MATTIAS),
        ).status_code
        == 400
    )
