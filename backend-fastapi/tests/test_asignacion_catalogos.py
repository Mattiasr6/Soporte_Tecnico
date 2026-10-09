"""T4: catalog endpoints of the asignacion module (/api/asignacion/...).

The old Supabase RLS rules (alembic/sql/0021_horarios/99_rls_reference.sql) are
enforced by the API: read = fn_puede_ver (any role but invitado), catalog
writes = fn_puede_editar, PC writes = fn_puede_operar, PC delete =
fn_puede_gestionar_auxiliares. Rows created here are removed at teardown.
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
DOMAIN = "test-asignacion-cat.local"
PREFIX = "ZZTEST-"


@pytest.fixture
def make_usuario() -> Iterator[Callable[..., Usuario]]:
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
            text(
                "delete from horarios.ambiente_pcs where ambiente_id in "
                "(select id from horarios.ambientes where codigo like :p)"
            ),
            {"p": f"{PREFIX}%"},
        )
        db.execute(
            text("delete from horarios.ambientes where codigo like :p"),
            {"p": f"{PREFIX}%"},
        )
        db.execute(
            text("delete from horarios.docentes where apellidos like :p"),
            {"p": f"{PREFIX}%"},
        )
        for table in ("materias", "carreras"):
            db.execute(
                text(f"delete from horarios.{table} where nombre like :p"),
                {"p": f"{PREFIX}%"},
            )
        db.execute(
            text("delete from horarios.feriados where descripcion like :p"),
            {"p": f"{PREFIX}%"},
        )
        for uid in created:
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


def _name() -> str:
    return f"{PREFIX}{uuid4().hex[:8]}"


def test_catalog_requires_token() -> None:
    assert client.get(f"{API}/materias").status_code == 401
    assert client.post(f"{API}/materias", json={"nombre": "x"}).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/carreras",
        "/docentes",
        "/materias",
        "/ambientes",
        "/ambiente-pcs",
        "/sistemas-academicos",
        "/bloques-horario",
        "/tipos-reserva",
        "/feriados",
    ],
)
def test_lists_are_readable_by_staff_and_hidden_from_invitado(
    make_usuario, path: str
) -> None:
    auxiliar = make_usuario("Auxiliar")
    r = client.get(f"{API}{path}", headers=_auth(auxiliar))
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)

    invitado = make_usuario("Tecnico")
    assert client.get(f"{API}{path}", headers=_auth(invitado)).status_code == 403


def test_seeded_catalogs_come_back_ordered(make_usuario) -> None:
    h = _auth(make_usuario("Auxiliar"))

    ambientes = client.get(f"{API}/ambientes?tipo=laboratorio", headers=h).json()
    codigos = [a["codigo"] for a in ambientes if a["codigo"].startswith("LAB-")]
    assert len(codigos) >= 10
    assert codigos == sorted(codigos)
    assert set(ambientes[0]) >= {
        "id",
        "codigo",
        "nombre",
        "tipo",
        "capacidad",
        "tipo_equipo",
        "ubicacion",
        "estado",
        "color",
        "orden",
    }

    bloques = client.get(f"{API}/bloques-horario", headers=h).json()
    assert len(bloques) >= 1
    assert [b["orden"] for b in bloques] == sorted(b["orden"] for b in bloques)
    assert len(bloques[0]["hora_inicio"]) == 8  # "HH:MM:SS" like PostgREST

    feriados = client.get(f"{API}/feriados", headers=h).json()
    assert len(feriados) >= 1
    assert [f["fecha"] for f in feriados] == sorted(f["fecha"] for f in feriados)

    assert len(client.get(f"{API}/carreras", headers=h).json()) >= 1
    assert len(client.get(f"{API}/tipos-reserva", headers=h).json()) >= 1
    sistemas = client.get(f"{API}/sistemas-academicos", headers=h).json()
    assert sistemas and all(s["activo"] for s in sistemas)
    assert isinstance(sistemas[0]["dias_permitidos"], list)


def test_auxiliar_cannot_write_academic_catalogs(make_usuario) -> None:
    h = _auth(make_usuario("Auxiliar"))
    r = client.post(f"{API}/materias", json={"nombre": _name()}, headers=h)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "42501"
    r = client.post(f"{API}/ambientes", json={"codigo": _name()}, headers=h)
    assert r.status_code == 403


def test_admin_materias_crud_round_trip(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    nombre = _name()
    r = client.post(
        f"{API}/materias", json={"nombre": nombre, "sigla": "ZZ"}, headers=h
    )
    assert r.status_code == 201, r.text
    materia = r.json()
    assert materia["nombre"] == nombre
    assert materia["requiere_laboratorio"] is True
    assert materia["activo"] is True

    r = client.patch(
        f"{API}/materias/{materia['id']}",
        json={"activo": False, "sigla": None},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is False
    assert r.json()["sigla"] is None
    assert r.json()["nombre"] == nombre

    listed = client.get(f"{API}/materias", headers=h).json()
    assert any(m["id"] == materia["id"] for m in listed)

    assert (
        client.delete(f"{API}/materias/{materia['id']}", headers=h).status_code == 204
    )
    assert (
        client.delete(f"{API}/materias/{materia['id']}", headers=h).status_code == 404
    )


def test_duplicate_name_is_409_with_db_message(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    nombre = _name()
    assert (
        client.post(f"{API}/materias", json={"nombre": nombre}, headers=h).status_code
        == 201
    )
    r = client.post(f"{API}/materias", json={"nombre": nombre}, headers=h)
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "23505"
    assert "materias_nombre_key" in detail["message"]


def test_admin_ambientes_crud_and_check_violation(make_usuario) -> None:
    h = _auth(make_usuario("Encargado"))
    codigo = _name()
    r = client.post(
        f"{API}/ambientes",
        json={
            "codigo": codigo,
            "capacidad": 20,
            "estado": "activo",
            "tipo": "laboratorio",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    ambiente = r.json()
    assert ambiente["color"] == "#2563eb"  # DB default

    r = client.patch(
        f"{API}/ambientes/{ambiente['id']}", json={"capacidad": -1}, headers=h
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "23514"

    r = client.patch(
        f"{API}/ambientes/{ambiente['id']}",
        json={"estado": "mantenimiento", "ubicacion": "Piso 9"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["ubicacion"]) == ("mantenimiento", "Piso 9")

    assert (
        client.delete(f"{API}/ambientes/{ambiente['id']}", headers=h).status_code == 204
    )


def test_unknown_fields_are_rejected(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    r = client.post(
        f"{API}/materias",
        json={"nombre": _name(), "creado_en": "2020-01-01"},
        headers=h,
    )
    assert r.status_code == 422


def test_pcs_permissions_trigger_message_and_embed(make_usuario) -> None:
    jefe = _auth(make_usuario("Jefe"))
    auxiliar = _auth(make_usuario("Auxiliar"))
    ambiente = client.post(
        f"{API}/ambientes", json={"codigo": _name()}, headers=jefe
    ).json()

    r = client.post(
        f"{API}/ambiente-pcs",
        json={"ambiente_id": ambiente["id"], "etiqueta": "PC01", "estado": "operativa"},
        headers=auxiliar,
    )
    assert r.status_code == 201, r.text
    pc = r.json()
    assert pc["cambio"] is None

    # Trigger fn_trg_pc_estado_controlado: an auxiliar cannot register a PC as baja.
    r = client.post(
        f"{API}/ambiente-pcs",
        json={
            "ambiente_id": ambiente["id"],
            "etiqueta": "PC02",
            "estado": "baja",
            "motivo_baja": "rota",
        },
        headers=auxiliar,
    )
    assert r.status_code == 422
    assert "administrador o el encargado" in r.json()["detail"]["message"]

    r = client.patch(
        f"{API}/ambiente-pcs/{pc['id']}", json={"ram": "16 GB"}, headers=auxiliar
    )
    assert r.status_code == 200, r.text
    assert r.json()["ram"] == "16 GB"

    listed = client.get(f"{API}/ambiente-pcs", headers=auxiliar).json()
    row = next(p for p in listed if p["id"] == pc["id"])
    assert "cambio" in row

    assert (
        client.delete(f"{API}/ambiente-pcs/{pc['id']}", headers=auxiliar).status_code
        == 403
    )
    assert (
        client.delete(f"{API}/ambiente-pcs/{pc['id']}", headers=jefe).status_code == 204
    )


def test_docente_with_relations(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    materia = client.post(f"{API}/materias", json={"nombre": _name()}, headers=h).json()
    carrera = client.post(f"{API}/carreras", json={"nombre": _name()}, headers=h).json()
    r = client.post(
        f"{API}/docentes", json={"nombres": "Ana", "apellidos": _name()}, headers=h
    )
    assert r.status_code == 201, r.text
    docente = r.json()
    assert docente["docente_carreras"] == []
    assert docente["docente_materias"] == []

    r = client.put(
        f"{API}/docentes/{docente['id']}/relaciones",
        json={"carreras": [carrera["id"]], "materias": [materia["id"]]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["docente_carreras"] == [{"carrera_id": carrera["id"]}]
    assert r.json()["docente_materias"] == [{"materia_id": materia["id"]}]

    listed = client.get(f"{API}/docentes", headers=h).json()
    row = next(d for d in listed if d["id"] == docente["id"])
    assert row["docente_materias"] == [{"materia_id": materia["id"]}]

    # Unknown materia id: FK violation surfaces as 409 and the old links survive.
    r = client.put(
        f"{API}/docentes/{docente['id']}/relaciones",
        json={"carreras": [], "materias": [999999999]},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "23503"
    listed = client.get(f"{API}/docentes", headers=h).json()
    row = next(d for d in listed if d["id"] == docente["id"])
    assert row["docente_carreras"] == [{"carrera_id": carrera["id"]}]

    assert (
        client.delete(f"{API}/docentes/{docente['id']}", headers=h).status_code == 204
    )


def test_feriados_upsert_by_fecha(make_usuario) -> None:
    h = _auth(make_usuario("Jefe"))
    fecha = "2099-12-31"
    r = client.put(f"{API}/feriados/{fecha}", json={"descripcion": _name()}, headers=h)
    assert r.status_code == 200, r.text
    nueva = _name()
    r = client.put(f"{API}/feriados/{fecha}", json={"descripcion": nueva}, headers=h)
    assert r.json() == {"fecha": fecha, "descripcion": nueva}
    assert client.delete(f"{API}/feriados/{fecha}", headers=h).status_code == 204
