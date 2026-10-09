"""G4: lab traffic-light board and day timeline (Django lab_tablero / lab_timeline).

Both are read-only queries over the horarios tables (no new table) and need
fn_puede_ver: every horarios rol but invitado reads the same rows through
/atenciones, /objetos-perdidos and /reportes-turno already.

Semaforo per lab (La Paz calendar days):
- rojo: at least one lost object still en_custodia and not "vencido" (found at
  most 90 days ago), same as Django's effective estado "pendiente";
- amarillo: a PC of the lab had an attention in the last 7 days, or a PC is in
  mantenimiento/baja, or a baja request is pending;
- verde: none of the above.
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
DOMAIN = "test-asignacion-tablero.local"
PREFIX = "ZZTB-"
DIA = "2026-01-15"


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


def _limpiar() -> None:
    with SessionLocal() as db:
        # Done tasks and delivered objects are protected by triggers.
        db.execute(text("set local session_replication_role = replica"))
        labs = "select id from horarios.ambientes where codigo like :p"
        params = {"p": f"{PREFIX}%"}
        for tabla in ("atenciones", "objetos_perdidos"):
            db.execute(
                text(f"delete from horarios.{tabla} where ambiente_id in ({labs})"),
                params,
            )
        db.execute(
            text("delete from horarios.reportes_turno where novedades like :p"), params
        )
        db.execute(
            text(
                "delete from horarios.solicitudes_baja where pc_id in (select id"
                f" from horarios.ambiente_pcs where ambiente_id in ({labs}))"
            ),
            params,
        )
        db.execute(text("delete from horarios.ambientes where codigo like :p"), params)
        db.commit()


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

    _limpiar()
    with SessionLocal() as db:
        for uid in created:
            db.execute(
                text("delete from horarios.perfiles where usuario_id = :uid"),
                {"uid": uid},
            )
            db.execute(text('delete from "Usuarios" where "Id" = :uid'), {"uid": uid})
        db.commit()


def _lab(db, pcs: int = 2) -> tuple[int, list[int]]:
    lab_id = db.execute(
        text(
            "insert into horarios.ambientes (codigo, nombre)"
            " values (:c, 'Lab tablero') returning id"
        ),
        {"c": f"{PREFIX}{uuid4().hex[:6]}"},
    ).scalar_one()
    pc_ids = [
        db.execute(
            text(
                "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, orden)"
                " values (:a, :e, :o) returning id"
            ),
            {"a": lab_id, "e": f"PC-{i + 1:02d}", "o": i},
        ).scalar_one()
        for i in range(pcs)
    ]
    return lab_id, pc_ids


def _atencion(db, lab_id: int, pc_id: int | None, hace: str, tipo="docente") -> int:
    return db.execute(
        text(
            "insert into horarios.atenciones (ambiente_id, pc_id, tipo, descripcion,"
            " creado_en) values (:a, :pc, :t, 'Prueba tablero',"
            " now() - cast(:hace as interval)) returning id"
        ),
        {"a": lab_id, "pc": pc_id, "t": tipo, "hace": hace},
    ).scalar_one()


def _objeto(db, lab_id: int, encontrado_en: str) -> int:
    return db.execute(
        text(
            "insert into horarios.objetos_perdidos (nombre, ambiente_id, foto_path,"
            " encontrado_en) values ('Mochila', :a, 'x/obj.jpg',"
            " cast(:en as timestamptz)) returning id"
        ),
        {"a": lab_id, "en": encontrado_en},
    ).scalar_one()


@pytest.fixture
def labs(make_usuario) -> dict[str, int]:
    """Six test labs, one per semaforo case (cleaned by make_usuario)."""
    with SessionLocal() as db:
        verde, _ = _lab(db)
        rojo, _ = _lab(db)
        _objeto(db, rojo, "now")
        vencido, _ = _lab(db)
        _objeto(db, vencido, "2025-01-01 10:00-04")
        atendido, pcs = _lab(db, pcs=3)
        _atencion(db, atendido, pcs[1], "2 days")
        _atencion(db, atendido, None, "1 hour", tipo="preventivo")
        viejo, pcs_viejo = _lab(db)
        _atencion(db, viejo, pcs_viejo[0], "10 days")
        mantenimiento, _ = _lab(db)
        db.execute(
            text(
                "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, estado)"
                " values (:a, 'PC-09', 'mantenimiento')"
            ),
            {"a": mantenimiento},
        )
        solicitud, pcs_sol = _lab(db)
        db.execute(
            text(
                "insert into horarios.solicitudes_baja (pc_id, motivo)"
                " values (:pc, 'No enciende')"
            ),
            {"pc": pcs_sol[0]},
        )
        db.commit()
    return {
        "verde": verde,
        "rojo": rojo,
        "vencido": vencido,
        "atendido": atendido,
        "viejo": viejo,
        "mantenimiento": mantenimiento,
        "solicitud": solicitud,
    }


def _tablero(usuario: Usuario) -> dict[int, dict]:
    r = client.get(f"{API}/tablero-laboratorios", headers=_auth(usuario))
    assert r.status_code == 200, r.text
    return {t["ambiente_id"]: t for t in r.json()}


def test_tablero_needs_ver(make_usuario) -> None:
    invitado = make_usuario("Invitado")
    r = client.get(f"{API}/tablero-laboratorios", headers=_auth(invitado))
    assert r.status_code == 403


def test_tablero_semaforo_rules(make_usuario, labs: dict[str, int]) -> None:
    tablero = _tablero(make_usuario("Tecnico"))
    esperado = {
        "verde": "verde",
        "rojo": "rojo",
        "vencido": "verde",
        "atendido": "amarillo",
        "viejo": "verde",
        "mantenimiento": "amarillo",
        "solicitud": "amarillo",
    }
    assert {k: tablero[v]["semaforo"] for k, v in labs.items()} == esperado
    assert tablero[labs["rojo"]]["objetos_en_custodia"] == 1
    assert tablero[labs["vencido"]]["objetos_en_custodia"] == 0
    assert tablero[labs["vencido"]]["objetos_vencidos"] == 1
    assert tablero[labs["mantenimiento"]]["pcs_mantenimiento"] == 1
    assert tablero[labs["solicitud"]]["solicitudes_baja_pendientes"] == 1


def test_tablero_counts_pcs_and_last_attention(
    make_usuario, labs: dict[str, int]
) -> None:
    tablero = _tablero(make_usuario("Auxiliar"))
    atendido = tablero[labs["atendido"]]
    assert atendido["total_pcs"] == 3
    assert atendido["pcs_atendidas_7d"] == ["PC-02"]
    assert atendido["atenciones_7d"] == 2
    # The newest attention wins, even a lab-level one.
    assert atendido["ultima"]["tipo"] == "preventivo"
    assert {"id", "creado_en", "tipo", "autor"} <= atendido["ultima"].keys()
    assert tablero[labs["verde"]]["ultima"] is None
    assert tablero[labs["viejo"]]["atenciones_7d"] == 0
    assert tablero[labs["viejo"]]["ultima"] is not None


@pytest.fixture
def eventos_del_dia(make_usuario) -> dict[str, int]:
    """One event of each kind on DIA (La Paz), plus one on the next day."""
    with SessionLocal() as db:
        lab_id, pcs = _lab(db)
        atencion = _atencion(db, lab_id, pcs[0], "0 days")
        db.execute(
            text(
                "update horarios.atenciones set creado_en = timestamptz"
                " '2026-01-15 10:00-04' where id = :id"
            ),
            {"id": atencion},
        )
        objeto = _objeto(db, lab_id, "2026-01-15 09:00-04")
        db.execute(text("set local app.limpiando_fotos = 'si'"))
        db.execute(
            text(
                "update horarios.objetos_perdidos set estado = 'entregado',"
                " entregado_a = 'Ana', entregado_en = timestamptz"
                " '2026-01-15 11:30-04', foto_entrega_path = 'x/ent.jpg'"
                " where id = :id"
            ),
            {"id": objeto},
        )
        reporte = db.execute(
            text(
                "insert into horarios.reportes_turno (fecha, turno, novedades,"
                " creado_en, foto_path) values (date '2026-01-15', 'T', :n,"
                " timestamptz '2026-01-15 18:00-04', 'x/rep.jpg') returning id"
            ),
            {"n": f"{PREFIX}sin novedades"},
        ).scalar_one()
        tarea = db.execute(
            text(
                "insert into horarios.reporte_tareas (reporte_id, ambiente_id,"
                " descripcion, hecha, hecha_en) values (:r, :a, 'Cambiar mouse',"
                " true, timestamptz '2026-01-15 12:00-04') returning id"
            ),
            {"r": reporte, "a": lab_id},
        ).scalar_one()
        # 23:30 La Paz on DIA is already the 16th in UTC: it must still count.
        tarde = _atencion(db, lab_id, None, "0 days")
        manana = _atencion(db, lab_id, None, "0 days")
        db.execute(
            text(
                "update horarios.atenciones set creado_en = case id"
                " when :t then timestamptz '2026-01-15 23:30-04'"
                " else timestamptz '2026-01-16 00:30-04' end where id in (:t, :m)"
            ),
            {"t": tarde, "m": manana},
        )
        db.commit()
    return {
        "atencion": atencion,
        "tarde": tarde,
        "manana": manana,
        "objeto": objeto,
        "reporte": reporte,
        "tarea": tarea,
        "lab": lab_id,
    }


def test_timeline_needs_ver(make_usuario) -> None:
    invitado = make_usuario("Invitado")
    r = client.get(f"{API}/timeline", headers=_auth(invitado))
    assert r.status_code == 403


def test_timeline_defaults_to_today_in_la_paz(make_usuario) -> None:
    r = client.get(f"{API}/timeline", headers=_auth(make_usuario("Tecnico")))
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        hoy = db.execute(
            text("select (now() at time zone 'America/La_Paz')::date")
        ).scalar_one()
    assert r.json()["fecha"] == hoy.isoformat()
    assert isinstance(r.json()["eventos"], list)


def test_timeline_rejects_bad_date(make_usuario) -> None:
    r = client.get(
        f"{API}/timeline",
        params={"fecha": "2026-13-01"},
        headers=_auth(make_usuario("Tecnico")),
    )
    assert r.status_code == 422


def test_timeline_lists_the_day_newest_first(
    make_usuario, eventos_del_dia: dict[str, int]
) -> None:
    r = client.get(
        f"{API}/timeline",
        params={"fecha": DIA},
        headers=_auth(make_usuario("Auxiliar")),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fecha"] == DIA
    ids = eventos_del_dia
    mios = [
        e
        for e in body["eventos"]
        if (
            e["evento"] == "atencion"
            and e["ref_id"] in (ids["atencion"], ids["tarde"], ids["manana"])
        )
        or (e["evento"].startswith("objeto") and e["ref_id"] == ids["objeto"])
        or (e["evento"] == "reporte" and e["ref_id"] == ids["reporte"])
        or (e["evento"] == "tarea_hecha" and e["ref_id"] == ids["tarea"])
    ]
    assert [(e["evento"], e["hora"]) for e in mios] == [
        ("atencion", "23:30"),
        ("reporte", "18:00"),
        ("tarea_hecha", "12:00"),
        ("objeto_entregado", "11:30"),
        ("atencion", "10:00"),
        ("objeto_registrado", "09:00"),
    ]
    por_evento = {e["evento"]: e for e in mios}
    assert por_evento["objeto_registrado"]["foto"] == "objeto"
    assert por_evento["objeto_entregado"]["foto"] == "entrega"
    assert por_evento["objeto_entregado"]["detalle"] == "Ana"
    assert por_evento["reporte"]["foto"] == "reporte"
    assert por_evento["atencion"]["foto"] is None
    assert por_evento["atencion"]["ambiente_id"] == ids["lab"]
    assert por_evento["tarea_hecha"]["ambiente_id"] == ids["lab"]
    assert por_evento["reporte"]["titulo"] == "T"
