"""Tests S13: alta/baja de usuarios, guards de acceso y el invariante INV-01.

Contra postgres-dev real. Los usuarios de prueba se crean con email bajo DOMINIO y el
fixture los borra (con sus atenciones) al salir, haya pasado lo que haya pasado.
"""

import os
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.base import SessionLocal
from app.main import app
from app.models.atencion import Atencion
from app.models.usuario import Usuario
from app.services.tokens import crear_token

UID_MATTIAS = 1
UID_TECNICO = 2
UID_JEFE = 8
DOMINIO = "test-s13.local"

client = TestClient(app)


def _token(uid: int) -> str:
    with SessionLocal() as db:
        usuario = db.get(Usuario, uid)
        assert usuario is not None, f"usuario {uid} no existe en la base de pruebas"
        return crear_token(
            usuario.id,
            usuario.display_name,
            usuario.role,
            usuario.email,
            os.environ["JWT_SECRET"],
        )


def h(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(uid)}"}


@pytest.fixture
def crear_usuario():
    creados: list[int] = []

    def _crear(email: str, **extra: object) -> dict[str, object]:
        cuerpo: dict[str, object] = {
            "email": email,
            "display_name": "Prueba S13",
            "role": "Tecnico",
        }
        cuerpo.update(extra)
        r = client.post("/api/usuarios", json=cuerpo, headers=h(UID_JEFE))
        assert r.status_code == 201, r.text
        datos = r.json()
        creados.append(datos["id"])
        return datos

    yield _crear

    with SessionLocal() as db:
        for uid in creados:
            db.execute(delete(Atencion).where(Atencion.usuario_id == uid))
            usuario = db.get(Usuario, uid)
            if usuario is not None:
                db.delete(usuario)
        db.commit()


def test_crear_usuario_queda_activo(crear_usuario):
    datos = crear_usuario(f"alta@{DOMINIO}")
    assert datos["display_name"] == "Prueba S13"
    assert datos["role"] == "Tecnico"
    assert datos["activo"] is True


def test_crear_sin_password_no_puede_entrar(crear_usuario):
    crear_usuario(f"sinclave@{DOMINIO}")
    r = client.post(
        "/api/auth/login",
        json={"email": f"sinclave@{DOMINIO}", "password": "Probando123"},
    )
    assert r.status_code == 401


def test_crear_email_duplicado(crear_usuario):
    crear_usuario(f"repe@{DOMINIO}")
    r = client.post(
        "/api/usuarios",
        json={"email": f"repe@{DOMINIO}", "display_name": "Otro", "role": "Tecnico"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 409, r.text


def test_crear_rol_invalido():
    r = client.post(
        "/api/usuarios",
        json={"email": f"rol@{DOMINIO}", "display_name": "X", "role": "Supervisor"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 400, r.text


def test_crear_password_corta():
    r = client.post(
        "/api/usuarios",
        json={
            "email": f"corta@{DOMINIO}",
            "display_name": "X",
            "role": "Tecnico",
            "password": "123",
        },
        headers=h(UID_JEFE),
    )
    assert r.status_code == 400, r.text


def test_tecnico_sin_permiso_no_crea():
    r = client.post(
        "/api/usuarios",
        json={"email": f"nope@{DOMINIO}", "display_name": "X", "role": "Tecnico"},
        headers=h(UID_TECNICO),
    )
    assert r.status_code == 403, r.text


def test_desactivar_y_reactivar(crear_usuario):
    uid = crear_usuario(f"baja@{DOMINIO}")["id"]
    r = client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": False}, headers=h(UID_JEFE)
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is False
    r = client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": True}, headers=h(UID_JEFE)
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is True


def test_tecnico_sin_permiso_no_desactiva(crear_usuario):
    uid = crear_usuario(f"baja2@{DOMINIO}")["id"]
    r = client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": False}, headers=h(UID_TECNICO)
    )
    assert r.status_code == 403, r.text


def test_jefe_no_puede_desactivarse_a_si_mismo():
    r = client.patch(
        f"/api/usuarios/{UID_JEFE}/activo", json={"activo": False}, headers=h(UID_JEFE)
    )
    assert r.status_code == 400, r.text


def test_desactivar_inexistente():
    r = client.patch(
        "/api/usuarios/999999/activo", json={"activo": False}, headers=h(UID_JEFE)
    )
    assert r.status_code == 404, r.text


def test_login_de_inactivo_es_403(crear_usuario):
    crear_usuario(f"baja3@{DOMINIO}", activo=False, password="Probando123")
    r = client.post(
        "/api/auth/login",
        json={"email": f"baja3@{DOMINIO}", "password": "Probando123"},
    )
    assert r.status_code == 403, r.text


def test_token_de_inactivo_es_401(crear_usuario):
    uid = crear_usuario(f"baja4@{DOMINIO}")["id"]
    token = "Bearer " + _token(uid)
    assert (
        client.get("/api/usuarios/me", headers={"Authorization": token}).status_code
        == 200
    )
    client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": False}, headers=h(UID_JEFE)
    )
    assert (
        client.get("/api/usuarios/me", headers={"Authorization": token}).status_code
        == 401
    )


def test_get_default_excluye_inactivos(crear_usuario):
    uid = crear_usuario(f"oculto@{DOMINIO}", activo=False)["id"]
    visibles = {
        u["id"] for u in client.get("/api/usuarios", headers=h(UID_JEFE)).json()
    }
    todos = {
        u["id"]
        for u in client.get(
            "/api/usuarios", params={"incluir_inactivos": "true"}, headers=h(UID_JEFE)
        ).json()
    }
    assert uid not in visibles
    assert uid in todos


def test_inv01_stats_incluyen_inactivos(crear_usuario):
    """El requisito central: dar de baja NO borra la historia del tecnico."""
    uid = crear_usuario(f"inv01@{DOMINIO}")["id"]
    with SessionLocal() as db:
        base = db.scalars(select(Atencion).limit(1)).first()
        assert base is not None
        db.add(
            Atencion(
                usuario_id=uid,
                grupo_padre_id=base.grupo_padre_id,
                grupo_id=base.grupo_id,
                area_id=base.area_id,
                area_solicitante="Administrativos",
                medio_solicitud="Interno",
                usuario_solicitante="ADM",
                categoria="Hardware",
                descripcion="TEST-S13 INV-01",
                solucion="n/a",
                fuera_de_turno=False,
                fecha_registro=date(2026, 3, 1),
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

    client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": False}, headers=h(UID_JEFE)
    )

    stats = client.get("/api/atenciones/stats", headers=h(UID_JEFE)).json()
    por_tecnico = {t["display_name"]: t["total"] for t in stats["por_tecnico"]}
    assert por_tecnico.get("Prueba S13") == 1

    listado = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    assert any(a["usuario_id"] == uid for a in listado)


def test_inv01_listado_muestra_el_nombre_del_inactivo(crear_usuario):
    uid = crear_usuario(f"inv01b@{DOMINIO}", display_name="Baja Con Historia")["id"]
    with SessionLocal() as db:
        base = db.scalars(select(Atencion).limit(1)).first()
        assert base is not None
        db.add(
            Atencion(
                usuario_id=uid,
                grupo_padre_id=base.grupo_padre_id,
                grupo_id=base.grupo_id,
                area_id=base.area_id,
                area_solicitante="Administrativos",
                medio_solicitud="Interno",
                usuario_solicitante="ADM",
                categoria="Hardware",
                descripcion="TEST-S13 INV-01b",
                solucion="n/a",
                fuera_de_turno=False,
                fecha_registro=date(2026, 3, 2),
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    client.patch(
        f"/api/usuarios/{uid}/activo", json={"activo": False}, headers=h(UID_JEFE)
    )
    listado = client.get("/api/atenciones", headers=h(UID_JEFE)).json()
    mias = [a for a in listado if a["usuario_id"] == uid]
    assert mias and mias[0]["usuario_nombre"] == "Baja Con Historia"
