"""T5: academic scheduling endpoints of the asignacion module.

Asignaciones, cesiones, reservas and reubicaciones are written through the
ported SQL RPCs (rpc_guardar_*, rpc_reubicar_clase); the anti-clash constraint
triggers are deferred, so a clash surfaces at COMMIT and must come back as an
HTTP error, never as a success. Occupancy/conflict queries wrap fn_ocupaciones,
fn_conflictos, fn_verificar_choques, fn_ambientes_libres* and
fn_estado_ambientes.

Old RLS rules (99_rls_reference.sql): read = fn_puede_ver, write =
fn_puede_editar (admin/decano/encargado; an auxiliar gets 403). Every row the
tests create is tagged with PREFIX and removed at teardown.
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
DOMAIN = "test-asignacion-hor.local"
PREFIX = "ZZHOR-"
# Far-future Mondays so seeded/dev data never overlaps.
LUNES = "2033-03-07"
LUNES_2 = "2033-03-14"
FIN = "2033-03-31"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(
            text("delete from horarios.reservas where titulo like :p"),
            {"p": f"{PREFIX}%"},
        )
        db.execute(
            text(
                "delete from horarios.asignaciones where docente_id in "
                "(select id from horarios.docentes where apellidos like :p)"
            ),
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
            text("delete from horarios.ambientes where codigo like :p"),
            {"p": f"{PREFIX}%"},
        )
        db.commit()


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

    _cleanup()
    with SessionLocal() as db:
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


@pytest.fixture
def catalogo() -> dict[str, int]:
    """Fresh carrera, materia, two docentes and a private laboratorio."""
    with SessionLocal() as db:

        def scalar(sql: str, **params: object) -> int:
            return int(db.execute(text(sql), params).scalar_one())

        ids = {
            "carrera": scalar(
                "insert into horarios.carreras (nombre) values (:n) returning id",
                n=_name(),
            ),
            "materia": scalar(
                "insert into horarios.materias (nombre) values (:n) returning id",
                n=_name(),
            ),
            "docente": scalar(
                "insert into horarios.docentes (nombres, apellidos) "
                "values ('Uno', :a) returning id",
                a=_name(),
            ),
            "docente2": scalar(
                "insert into horarios.docentes (nombres, apellidos) "
                "values ('Dos', :a) returning id",
                a=_name(),
            ),
            "ambiente": scalar(
                "insert into horarios.ambientes (codigo, nombre, tipo) "
                "values (:c, 'Lab prueba', 'laboratorio') returning id",
                c=_name(),
            ),
            "sistema": scalar(
                "select id from horarios.sistemas_academicos where codigo = 'SEMESTRAL'"
            ),
        }
        db.commit()
    yield ids
    _cleanup()


def _asignacion_payload(c: dict[str, int], docente: str = "docente", **kw) -> dict:
    return {
        "sistema_id": c["sistema"],
        "docente_id": c[docente],
        "materia_id": c["materia"],
        "carrera_id": c["carrera"],
        "grupo": "A",
        "fecha_inicio": LUNES,
        "fecha_fin": FIN,
        "observacion": None,
        "fechas": [],
        "horarios": [
            {
                "dia_semana": 1,
                "hora_inicio": kw.get("hora_inicio", "07:00"),
                "hora_fin": kw.get("hora_fin", "09:00"),
                "ambiente_id": c["ambiente"],
            }
        ],
    }


# --- auth / permissions ---------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/asignaciones",
        "/cesiones",
        "/reservas",
        f"/ocupaciones?desde={LUNES}&hasta={FIN}",
        f"/conflictos?desde={LUNES}&hasta={FIN}",
        "/estado-ambientes",
    ],
)
def test_scheduling_reads_need_token_and_staff(make_usuario, path: str) -> None:
    assert client.get(f"{API}{path}").status_code == 401
    r = client.get(f"{API}{path}", headers=_auth(make_usuario("Auxiliar")))
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
    invitado = make_usuario("Tecnico")
    assert client.get(f"{API}{path}", headers=_auth(invitado)).status_code == 403


def test_auxiliar_cannot_write_scheduling(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Auxiliar"))
    r = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "42501"
    r = client.post(
        f"{API}/reservas",
        json={"tipo_id": 1, "titulo": _name(), "horarios": []},
        headers=h,
    )
    assert r.status_code == 403
    assert client.post(f"{API}/asignaciones", json={}).status_code == 401


# --- asignaciones -----------------------------------------------------------------


def test_asignacion_create_read_update_delete(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    r = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    )
    assert r.status_code == 201, r.text
    creada = r.json()
    assert creada["docente"]["id"] == catalogo["docente"]
    assert creada["materia"]["id"] == catalogo["materia"]
    assert creada["carrera"]["id"] == catalogo["carrera"]
    assert len(creada["horarios"]) == 1
    horario = creada["horarios"][0]
    assert horario["hora_inicio"] == "07:00:00"
    assert creada["fechas"] == []

    detalle = client.get(f"{API}/asignaciones/{creada['id']}", headers=h).json()
    assert detalle["id"] == creada["id"]

    lista = client.get(f"{API}/asignaciones?fin_desde={LUNES}", headers=h).json()
    assert creada["id"] in [a["id"] for a in lista]
    por_ambiente = client.get(
        f"{API}/asignaciones?ambiente_id={catalogo['ambiente']}", headers=h
    ).json()
    assert [a["id"] for a in por_ambiente] == [creada["id"]]

    cambio = _asignacion_payload(catalogo, hora_inicio="09:00", hora_fin="11:00")
    cambio["horarios"][0]["id"] = horario["id"]
    r = client.put(f"{API}/asignaciones/{creada['id']}", json=cambio, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["horarios"][0]["hora_inicio"] == "09:00:00"

    assert (
        client.delete(f"{API}/asignaciones/{creada['id']}", headers=h).status_code
        == 204
    )
    assert (
        client.get(f"{API}/asignaciones/{creada['id']}", headers=h).status_code == 404
    )


def test_overlapping_asignacion_is_rejected_at_commit(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    r = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    )
    assert r.status_code == 201, r.text

    choque = _asignacion_payload(
        catalogo, "docente2", hora_inicio="08:00", hora_fin="10:00"
    )
    r = client.post(f"{API}/asignaciones", json=choque, headers=h)
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "P0001"
    assert detail["message"]

    # Nothing of the rejected asignacion was kept.
    lista = client.get(
        f"{API}/asignaciones?ambiente_id={catalogo['ambiente']}", headers=h
    ).json()
    assert len(lista) == 1


def test_rpc_validation_error_is_422(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    payload = _asignacion_payload(catalogo)
    payload["horarios"] = []
    r = client.post(f"{API}/asignaciones", json=payload, headers=h)
    assert r.status_code == 422
    assert "al menos un horario" in r.json()["detail"]["message"]


# --- occupancy queries --------------------------------------------------------------


def test_occupancy_queries_see_the_asignacion(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    creada = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    ).json()

    ocupaciones = client.get(
        f"{API}/ocupaciones?desde={LUNES}&hasta={LUNES}", headers=h
    ).json()
    propias = [o for o in ocupaciones if o["asignacion_id"] == creada["id"]]
    assert len(propias) == 1
    assert propias[0]["ambiente_id"] == catalogo["ambiente"]
    assert propias[0]["origen"] == "clase"

    libres = client.post(
        f"{API}/ambientes-libres",
        json={"fecha": LUNES, "hora_inicio": "08:00", "hora_fin": "09:00"},
        headers=h,
    )
    assert libres.status_code == 200, libres.text
    assert catalogo["ambiente"] not in [a["id"] for a in libres.json()]
    libres = client.post(
        f"{API}/ambientes-libres",
        json={
            "fecha": LUNES,
            "hora_inicio": "08:00",
            "hora_fin": "09:00",
            "ignorar": {"asignacion_horario_id": creada["horarios"][0]["id"]},
        },
        headers=h,
    ).json()
    assert catalogo["ambiente"] in [a["id"] for a in libres]

    libres_fechas = client.post(
        f"{API}/ambientes-libres/fechas",
        json={"fechas": [LUNES, LUNES_2], "hora_inicio": "10:00", "hora_fin": "11:00"},
        headers=h,
    )
    assert libres_fechas.status_code == 200, libres_fechas.text
    assert catalogo["ambiente"] in [a["id"] for a in libres_fechas.json()]

    choques = client.post(
        f"{API}/choques/verificar",
        json={
            "items": [
                {
                    "fecha": LUNES,
                    "hora_inicio": "08:00",
                    "hora_fin": "09:00",
                    "ambiente_id": catalogo["ambiente"],
                    "docente_id": catalogo["docente2"],
                }
            ]
        },
        headers=h,
    )
    assert choques.status_code == 200, choques.text
    assert any(c["asignacion_id"] == creada["id"] for c in choques.json())

    conflictos = client.get(
        f"{API}/conflictos?desde={LUNES}&hasta={FIN}", headers=h
    ).json()
    assert not [
        c for c in conflictos if creada["id"] in (c["asignacion_a"], c["asignacion_b"])
    ]


# --- reservas / reubicaciones / cesiones -------------------------------------------


def test_reserva_create_list_delete(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    titulo = _name()
    r = client.post(
        f"{API}/reservas",
        json={
            "tipo_id": 1,
            "titulo": titulo,
            "categoria": "taller",
            "horarios": [
                {
                    "ambiente_id": catalogo["ambiente"],
                    "fecha": LUNES,
                    "hora_inicio": "14:00",
                    "hora_fin": "16:00",
                }
            ],
            "reubicaciones": [],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    reserva = r.json()
    assert reserva["titulo"] == titulo
    assert reserva["tipo"]["codigo"] == "EVENTO"
    assert len(reserva["horarios"]) == 1
    assert reserva["reubicaciones"] == []

    lista = client.get(f"{API}/reservas", headers=h).json()
    assert reserva["id"] in [x["id"] for x in lista]
    assert client.get(f"{API}/reservas/{reserva['id']}", headers=h).status_code == 200

    ocupaciones = client.get(
        f"{API}/ocupaciones?desde={LUNES}&hasta={LUNES}", headers=h
    ).json()
    assert any(o["reserva_id"] == reserva["id"] for o in ocupaciones)

    assert (
        client.delete(f"{API}/reservas/{reserva['id']}", headers=h).status_code == 204
    )


def test_reubicar_and_ceder_clase(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    creada = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    ).json()
    horario_id = creada["horarios"][0]["id"]

    r = client.post(
        f"{API}/reubicaciones",
        json={
            "asignacion_horario_id": horario_id,
            "fecha": LUNES,
            "ambiente_destino_id": None,
            "motivo": "Suspendida por prueba",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    reubicacion_id = r.json()["id"]
    assert (
        client.delete(f"{API}/reubicaciones/{reubicacion_id}", headers=h).status_code
        == 204
    )

    r = client.post(
        f"{API}/cesiones/lotes",
        json={
            "docente_receptor_id": catalogo["docente2"],
            "motivo": "Prueba",
            "horarios": [{"asignacion_horario_id": horario_id, "fechas": [LUNES_2]}],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    lote = r.json()["lote"]

    cesiones = client.get(f"{API}/cesiones?lote={lote}", headers=h).json()
    assert len(cesiones) == 1
    cesion = cesiones[0]
    assert cesion["receptor"]["id"] == catalogo["docente2"]
    assert cesion["fechas"] == [{"fecha": LUNES_2}]
    assert cesion["horario"]["asignacion"]["id"] == creada["id"]
    assert client.get(f"{API}/cesiones/{cesion['id']}", headers=h).status_code == 200
    por_horario = client.get(
        f"{API}/cesiones?asignacion_horario_id={horario_id}", headers=h
    ).json()
    assert [c["id"] for c in por_horario] == [cesion["id"]]
    assert (
        client.get(
            f"{API}/cesiones?asignacion_horario_id={horario_id}&excluir_lote={lote}",
            headers=h,
        ).json()
        == []
    )

    assert client.delete(f"{API}/cesiones/{cesion['id']}", headers=h).status_code == 204


def test_vincular_docente_adds_without_replacing(make_usuario, catalogo) -> None:
    h = _auth(make_usuario("Jefe"))
    docente = catalogo["docente"]
    r = client.post(
        f"{API}/docentes/{docente}/vinculos",
        json={"carreras": [catalogo["carrera"]], "materias": []},
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{API}/docentes/{docente}/vinculos",
        json={"carreras": [], "materias": [catalogo["materia"]]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["docente_carreras"] == [{"carrera_id": catalogo["carrera"]}]
    assert body["docente_materias"] == [{"materia_id": catalogo["materia"]}]


# --- SQL 34: save a class even if its laboratorio is busy some days -------------


def test_asignacion_moves_busy_days_to_another_ambiente(make_usuario, catalogo) -> None:
    """rpc_guardar_asignacion stores p.reubicaciones in the same operation."""
    h = _auth(make_usuario("Jefe"))
    with SessionLocal() as db:
        otro_lab = int(
            db.execute(
                text(
                    "insert into horarios.ambientes (codigo, nombre, tipo) "
                    "values (:c, 'Lab destino', 'laboratorio') returning id"
                ),
                {"c": _name()},
            ).scalar_one()
        )
        db.commit()

    # An event already occupies the laboratorio on the first Monday.
    r = client.post(
        f"{API}/reservas",
        json={
            "tipo_id": 1,
            "titulo": _name(),
            "categoria": "taller",
            "horarios": [
                {
                    "ambiente_id": catalogo["ambiente"],
                    "fecha": LUNES,
                    "hora_inicio": "07:00",
                    "hora_fin": "09:00",
                }
            ],
            "reubicaciones": [],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    reserva_id = r.json()["id"]

    # Without saying where the class goes that day, the clash still blocks.
    r = client.post(
        f"{API}/asignaciones", json=_asignacion_payload(catalogo), headers=h
    )
    assert r.status_code == 422, r.text

    reubicacion = {
        "dia_semana": 1,
        "hora_inicio": "07:00",
        "ambiente_id": catalogo["ambiente"],
        "fecha": LUNES,
        "ambiente_destino_id": catalogo["ambiente"],
        "aula_destino": None,
        "reserva_id": reserva_id,
        "motivo": "Laboratorio ocupado: evento",
    }
    # The destination must be a different ambiente.
    r = client.post(
        f"{API}/asignaciones",
        json={**_asignacion_payload(catalogo), "reubicaciones": [reubicacion]},
        headers=h,
    )
    assert r.status_code == 422, r.text
    assert "otro laboratorio" in r.json()["detail"]["message"]

    reubicacion["ambiente_destino_id"] = otro_lab
    r = client.post(
        f"{API}/asignaciones",
        json={**_asignacion_payload(catalogo), "reubicaciones": [reubicacion]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    creada = r.json()
    horario_id = creada["horarios"][0]["id"]

    guardadas = client.get(
        f"{API}/reubicaciones?asignacion_horario_id={horario_id}", headers=h
    )
    assert guardadas.status_code == 200, guardadas.text
    [guardada] = guardadas.json()
    assert guardada["asignacion_horario_id"] == horario_id
    assert guardada["fecha"] == LUNES
    assert guardada["ambiente_destino_id"] == otro_lab
    assert guardada["aula_destino"] is None
    assert guardada["reserva_id"] == reserva_id

    # Editing again with an aula instead upserts the same day.
    payload = _asignacion_payload(catalogo)
    payload["horarios"][0]["id"] = horario_id
    payload["reubicaciones"] = [
        {**reubicacion, "ambiente_destino_id": None, "aula_destino": "Aula 201"}
    ]
    r = client.put(f"{API}/asignaciones/{creada['id']}", json=payload, headers=h)
    assert r.status_code == 200, r.text
    [editada] = client.get(
        f"{API}/reubicaciones?asignacion_horario_id={horario_id}", headers=h
    ).json()
    assert editada["ambiente_destino_id"] is None
    assert editada["aula_destino"] == "Aula 201"

    invitado = _auth(make_usuario("Tecnico"))
    assert (
        client.get(
            f"{API}/reubicaciones?asignacion_horario_id={horario_id}",
            headers=invitado,
        ).status_code
        == 403
    )
