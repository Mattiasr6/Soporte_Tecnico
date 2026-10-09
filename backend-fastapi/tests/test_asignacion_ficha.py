"""G8: lab hardware sheet ("ficha del lab") on `horarios.ambientes`.

Ported from Django `auxiliares/laboratorios/<id>/pcs/` (`views_lab.py`
`FICHA_CAMPOS`, Soporte `Laboratorios` columns). The sheet is the lab's
declared standard spec; the per-PC values stay in `horarios.ambiente_pcs`.

- New nullable columns: procesador (<=200), ram, almacenamiento (Django
  "disco", named like `ambiente_pcs.almacenamiento`), marca, gpu, monitores
  (<=100 each), sillas, pcs_estudiantes, pcs_docentes (>= 0).
- `capacidad` already exists (NOT NULL, >= 0) and is shared with the academic
  assignment; the sheet can change it but never clear it.
- Read: fn_puede_ver (GET /ambientes). Write: PUT /ambientes/{id}/ficha with
  fn_puede_gestionar_auxiliares (Django `puede_ficha`: Jefe/Encargado).
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario
from app.services.tokens import crear_token

client = TestClient(app)
API = "/api/asignacion"
DOMAIN = "test-asignacion-ficha.local"
PREFIX = "ZZFI-"

FICHA_TEXTO = ("procesador", "ram", "almacenamiento", "marca", "gpu", "monitores")
FICHA_ENTEROS = ("sillas", "pcs_estudiantes", "pcs_docentes")


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_usuario() -> Iterator[Callable[[str], Usuario]]:
    created: list[int] = []

    def _make(role: str) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"Prueba {role}",
                role=role,
                activo=True,
                created_at=now,
                updated_at=now,
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)
            db.expunge(usuario)
        created.append(usuario.id)
        return usuario

    yield _make

    with SessionLocal() as db:
        db.execute(
            text("delete from horarios.ambientes where codigo like :p"),
            {"p": f"{PREFIX}%"},
        )
        for uid in created:
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


@pytest.fixture
def lab() -> int:
    with SessionLocal() as db:
        lab_id = db.execute(
            text(
                "insert into horarios.ambientes (codigo, nombre, capacidad)"
                " values (:c, 'Lab ficha', 30) returning id"
            ),
            {"c": f"{PREFIX}{uuid4().hex[:6]}"},
        ).scalar_one()
        db.commit()
    return lab_id


def _ambiente(h: dict[str, str], lab_id: int) -> dict:
    found = client.get(f"{API}/ambientes", headers=h).json()
    return next(a for a in found if a["id"] == lab_id)


FICHA = {
    "procesador": "  Intel Core i5-12400  ",
    "ram": "16 GB",
    "almacenamiento": "SSD 512 GB",
    "marca": "HP",
    "gpu": "",
    "monitores": "22 pulgadas",
    "sillas": 32,
    "capacidad": 30,
    "pcs_estudiantes": 30,
    "pcs_docentes": 1,
}


def test_ambientes_expose_empty_sheet(make_usuario, lab) -> None:
    ambiente = _ambiente(_auth(make_usuario("Tecnico")), lab)
    for campo in FICHA_TEXTO + FICHA_ENTEROS:
        assert ambiente[campo] is None, campo
    assert ambiente["capacidad"] == 30


def test_jefe_saves_sheet_trims_and_clears_blanks(make_usuario, lab) -> None:
    h = _auth(make_usuario("Jefe"))
    r = client.put(f"{API}/ambientes/{lab}/ficha", json=FICHA, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["procesador"] == "Intel Core i5-12400"
    assert body["gpu"] is None  # blank = cleared, as in Django
    assert (body["sillas"], body["pcs_estudiantes"], body["pcs_docentes"]) == (
        32,
        30,
        1,
    )

    # read back through the list every role uses
    leido = _ambiente(_auth(make_usuario("Decano")), lab)
    assert leido["almacenamiento"] == "SSD 512 GB"
    assert leido["monitores"] == "22 pulgadas"


def test_put_replaces_whole_sheet_and_keeps_capacity_when_omitted(
    make_usuario, lab
) -> None:
    h = _auth(make_usuario("Encargado"))
    assert (
        client.put(f"{API}/ambientes/{lab}/ficha", json=FICHA, headers=h).status_code
        == 200
    )
    r = client.put(f"{API}/ambientes/{lab}/ficha", json={"ram": "8 GB"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ram"] == "8 GB"
    assert body["procesador"] is None
    assert body["sillas"] is None
    assert body["capacidad"] == 30  # omitted or null capacidad is kept

    r = client.put(f"{API}/ambientes/{lab}/ficha", json={"capacidad": None}, headers=h)
    assert r.status_code == 200
    assert r.json()["capacidad"] == 30

    r = client.put(f"{API}/ambientes/{lab}/ficha", json={"capacidad": 24}, headers=h)
    assert r.json()["capacidad"] == 24


@pytest.mark.parametrize("role", ["Auxiliar", "Tecnico", "Decano"])
def test_only_jefe_or_encargado_write_the_sheet(make_usuario, lab, role) -> None:
    h = _auth(make_usuario(role))
    r = client.put(f"{API}/ambientes/{lab}/ficha", json=FICHA, headers=h)
    assert r.status_code == 403
    assert _ambiente(h, lab)["procesador"] is None


def test_invalid_values_are_422(make_usuario, lab) -> None:
    h = _auth(make_usuario("Jefe"))
    for cuerpo in (
        {"sillas": -1},
        {"pcs_docentes": -3},
        {"capacidad": -1},
        {"procesador": "x" * 201},
        {"ram": "x" * 101},
        {"desconocido": "x"},
    ):
        r = client.put(f"{API}/ambientes/{lab}/ficha", json=cuerpo, headers=h)
        assert r.status_code == 422, cuerpo


def test_missing_lab_is_404(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    r = client.put(f"{API}/ambientes/999999999/ficha", json=FICHA, headers=h)
    assert r.status_code == 404
