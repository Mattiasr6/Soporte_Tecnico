"""T6a: auxiliar shifts and shift reports of the asignacion module.

Tables turnos_programados, horarios_turno, turnos_trabajo,
reportes_turno and reporte_tareas plus fn_turno_vigente, fn_asignar_turno and
fn_limpiar_fotos_reporte. The closing photo (old Supabase bucket
`reportes-turno`) is stored on disk by the API.

Old RLS rules (99_rls_reference.sql) enforced by the API:
- read everything here: fn_puede_ver (invitado -> 403);
- turnos_programados, horarios_turno, fn_asignar_turno:
  fn_puede_gestionar_auxiliares (admin/encargado; auxiliar -> 403);
- reportes_turno create: fn_puede_operar and (own report or gestionar) and
  fn_puede_cerrar_turno(turno); update/delete: fn_puede_editar_reporte (gestionar,
  or own report of today in America/La_Paz while fn_puede_cerrar_turno holds).
Every row the tests create is tagged and removed at teardown; photos go to a
temporary directory, never to the real data dir.
"""

import io
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.core.config import settings
from app.db.base import SessionLocal
from app.main import app
from app.models.usuario import Usuario
from app.services.tokens import crear_token

client = TestClient(app)
API = "/api/asignacion"
DOMAIN = "test-asignacion-tur.local"
PREFIX = "ZZTUR-"


def _hoy() -> datetime:
    return datetime.now(ZoneInfo("America/La_Paz"))


def _iso(days: int = 0) -> str:
    return (_hoy().date() + timedelta(days=days)).isoformat()


def _auth(usuario: Usuario) -> dict[str, str]:
    token = crear_token(
        usuario.id,
        usuario.display_name,
        usuario.role,
        usuario.email,
        os.environ["JWT_SECRET"],
    )
    return {"Authorization": f"Bearer {token}"}


def _perfil_id(usuario: Usuario) -> str:
    r = client.get(f"{API}/me", headers=_auth(usuario))
    assert r.status_code == 200, r.text
    return r.json()["perfil_id"]


def _png(size: int = 4) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _cleanup() -> None:
    with SessionLocal() as db:
        # Done tasks and reports with done tasks are protected by triggers.
        # Replica mode also skips ON DELETE CASCADE, so tasks go first.
        db.execute(text("set local session_replication_role = replica"))
        mine = (
            "select id from horarios.reportes_turno where novedades like :p or "
            "auxiliar_id in (select id from horarios.perfiles where correo like :d)"
        )
        params = {"p": f"{PREFIX}%", "d": f"%@{DOMAIN}"}
        db.execute(
            text(f"delete from horarios.reporte_tareas where reporte_id in ({mine})"),
            params,
        )
        db.execute(
            text(f"delete from horarios.reportes_turno where id in ({mine})"), params
        )
        db.execute(text("set local session_replication_role = origin"))
        db.execute(
            text("delete from horarios.turnos_trabajo where notas_apertura like :p"),
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


@pytest.fixture
def horarios_restaurados() -> Iterator[None]:
    """Snapshot horarios_turno and restore it (some tests change shift hours)."""
    with SessionLocal() as db:
        antes = db.execute(
            text("select turno, hora_inicio, hora_fin from horarios.horarios_turno")
        ).all()
    yield
    with SessionLocal() as db:
        for turno, inicio, fin in antes:
            db.execute(
                text(
                    "update horarios.horarios_turno set hora_inicio = :i, hora_fin = :f"
                    " where turno = :t"
                ),
                {"t": turno, "i": inicio, "f": fin},
            )
        db.commit()


@pytest.fixture
def fotos_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ASIGNACION_DATA_DIR", str(tmp_path))
    return tmp_path / "reportes-turno"


@pytest.fixture
def equipo(make_usuario, horarios_restaurados) -> dict:
    """Two auxiliares on shift M since yesterday, an encargado and an invitado.

    Shift M starts at 00:00 during the test, so fn_puede_cerrar_turno('M') holds
    for the auxiliares whatever the time of day the suite runs.
    """
    aux, aux2 = make_usuario("Auxiliar"), make_usuario("Auxiliar")
    enc, inv = make_usuario("Encargado"), make_usuario("Invitado")
    ids = {"aux_perfil": _perfil_id(aux), "aux2_perfil": _perfil_id(aux2)}
    with SessionLocal() as db:
        for pid in ids.values():
            db.execute(
                text(
                    "insert into horarios.turnos_programados (perfil_id, turno, desde)"
                    " values (cast(:p as uuid), 'M', cast(:d as date))"
                ),
                {"p": pid, "d": _iso(-1)},
            )
        db.execute(
            text(
                "update horarios.horarios_turno set hora_inicio = '00:00'"
                " where turno = 'M'"
            )
        )
        db.commit()
    return {"aux": aux, "aux2": aux2, "enc": enc, "inv": inv, **ids}


def _crear_reporte(usuario: Usuario, turno: str = "M", **extra) -> dict:
    body = {"turno": turno, "novedades": f"{PREFIX}novedad", "tareas": [], **extra}
    return client.post(f"{API}/reportes-turno", json=body, headers=_auth(usuario))


def _reporte_de_ayer(perfil_id: str) -> int:
    with SessionLocal() as db:
        rid = db.execute(
            text(
                "insert into horarios.reportes_turno (fecha, turno, auxiliar_id, novedades)"
                " values (cast(:f as date), 'M', cast(:p as uuid), :n) returning id"
            ),
            {"f": _iso(-1), "p": perfil_id, "n": f"{PREFIX}ayer"},
        ).scalar_one()
        db.commit()
    return int(rid)


# --- auth ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/turnos-programados",
        "/turnos/vigente",
        "/horarios-turno",
        "/auxiliares",
        "/reportes-turno",
        "/reporte-tareas/pendientes",
        "/turnos-trabajo/estado",
    ],
)
def test_reads_need_token_and_staff(make_usuario, path: str) -> None:
    assert client.get(f"{API}{path}").status_code == 401
    r = client.get(f"{API}{path}", headers=_auth(make_usuario("Auxiliar")))
    assert r.status_code == 200, r.text
    invitado = make_usuario("Invitado")
    assert client.get(f"{API}{path}", headers=_auth(invitado)).status_code == 403


# --- turnos programados / vigente ------------------------------------------------


def test_encargado_programs_shifts_and_auxiliar_sees_own_vigente(make_usuario) -> None:
    aux, enc = make_usuario("Auxiliar"), make_usuario("Encargado")
    pid = _perfil_id(aux)
    body = {"desde": _iso(-2), "filas": [{"perfil_id": pid, "turno": "T"}]}

    denied = client.put(f"{API}/turnos-programados", json=body, headers=_auth(aux))
    assert denied.status_code == 403

    ok = client.put(f"{API}/turnos-programados", json=body, headers=_auth(enc))
    assert ok.status_code == 200, ok.text
    # Same perfil and date again = change it (upsert on perfil_id, desde).
    body["filas"][0]["turno"] = "N"
    assert (
        client.put(
            f"{API}/turnos-programados", json=body, headers=_auth(enc)
        ).status_code
        == 200
    )

    vigente = client.get(f"{API}/turnos/vigente", headers=_auth(aux))
    assert vigente.status_code == 200, vigente.text
    assert vigente.json()["turno"] == "N"
    assert vigente.json()["perfil_id"] == pid

    lista = client.get(f"{API}/turnos-programados", headers=_auth(aux)).json()
    mios = [t for t in lista if t["perfil_id"] == pid]
    assert len(mios) == 1
    assert mios[0]["perfil"]["nombre_completo"] == "Prueba Auxiliar"

    assert (
        client.delete(
            f"{API}/turnos-programados/{mios[0]['id']}", headers=_auth(aux)
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"{API}/turnos-programados/{mios[0]['id']}", headers=_auth(enc)
        ).status_code
        == 204
    )
    vigente = client.get(f"{API}/turnos/vigente", headers=_auth(aux)).json()
    assert vigente["turno"] is None


def test_assign_usual_shift_is_for_managers(make_usuario) -> None:
    aux, enc = make_usuario("Auxiliar"), make_usuario("Encargado")
    pid = _perfil_id(aux)
    body = {"turno": "T", "sabado": True}
    url = f"{API}/auxiliares/{pid}/turno"

    assert client.put(url, json=body, headers=_auth(aux)).status_code == 403
    r = client.put(url, json=body, headers=_auth(enc))
    assert r.status_code == 204, r.text

    lista = client.get(
        f"{API}/auxiliares", params={"rol": "auxiliar"}, headers=_auth(aux)
    ).json()
    fila = next(p for p in lista if p["id"] == pid)
    assert fila["turno_habitual"] == "T"
    assert fila["sabado_rotativo"] is True
    assert all(p["rol"] == "auxiliar" for p in lista)

    personal = client.get(
        f"{API}/auxiliares",
        params=[("rol", "auxiliar"), ("rol", "encargado"), ("activo", "true")],
        headers=_auth(aux),
    ).json()
    assert {p["rol"] for p in personal} <= {"auxiliar", "encargado"}
    assert any(p["rol"] == "encargado" for p in personal)


def test_shift_hours_are_edited_by_managers(make_usuario, horarios_restaurados) -> None:
    aux, enc = make_usuario("Auxiliar"), make_usuario("Encargado")
    lista = client.get(f"{API}/horarios-turno", headers=_auth(aux)).json()
    assert [h["turno"] for h in lista] == ["M", "MD", "T", "N"]

    body = [{"turno": "N", "hora_inicio": "18:00", "hora_fin": "22:30"}]
    assert (
        client.put(f"{API}/horarios-turno", json=body, headers=_auth(aux)).status_code
        == 403
    )
    r = client.put(f"{API}/horarios-turno", json=body, headers=_auth(enc))
    assert r.status_code == 200, r.text
    n = next(h for h in r.json() if h["turno"] == "N")
    assert n["hora_fin"] == "22:30:00"

    invalid = [{"turno": "N", "hora_inicio": "22:00", "hora_fin": "18:00"}]
    bad = client.put(f"{API}/horarios-turno", json=invalid, headers=_auth(enc))
    assert bad.status_code == 422


# --- turnos de trabajo ---------------------------------------------------------


def test_open_and_close_work_shift(make_usuario) -> None:
    aux, inv = make_usuario("Auxiliar"), make_usuario("Invitado")
    body = {"turno": "M", "es_sabado_rotativo": False, "notas": f"{PREFIX}abre"}
    assert (
        client.post(f"{API}/turnos-trabajo", json=body, headers=_auth(inv)).status_code
        == 403
    )

    r = client.post(f"{API}/turnos-trabajo", json=body, headers=_auth(aux))
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    estado = client.get(f"{API}/turnos-trabajo/estado", headers=_auth(aux)).json()
    assert estado["abierto"]["id"] == tid
    assert estado["abierto"]["apertura"]["nombre_completo"] == "Prueba Auxiliar"

    c = client.post(
        f"{API}/turnos-trabajo/{tid}/cierre",
        json={"notas": "pase"},
        headers=_auth(aux),
    )
    assert c.status_code == 200, c.text
    estado = client.get(f"{API}/turnos-trabajo/estado", headers=_auth(aux)).json()
    assert estado["abierto"] is None
    assert estado["ultimo_cerrado"]["id"] == tid


# --- reportes de turno ---------------------------------------------------------


def test_auxiliar_creates_own_report_only_for_current_shift(equipo) -> None:
    aux = equipo["aux"]
    r = _crear_reporte(
        aux, tareas=[{"descripcion": "Revisar PC 3", "ambiente_id": None}]
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    lista = client.get(f"{API}/reportes-turno", headers=_auth(aux)).json()
    rep = next(x for x in lista if x["id"] == rid)
    assert rep["auxiliar_id"] == equipo["aux_perfil"]
    assert rep["autor"]["nombre_completo"] == "Prueba Auxiliar"
    assert [t["descripcion"] for t in rep["tareas"]] == ["Revisar PC 3"]
    assert rep["turno_realizado"] is not None

    # Not the auxiliar's vigente shift -> fn_puede_cerrar_turno is false.
    assert _crear_reporte(aux, turno="N").status_code == 403
    # Writing a report on behalf of someone else needs gestionar.
    other = _crear_reporte(aux, auxiliar_id=equipo["aux2_perfil"])
    assert other.status_code == 403
    # Invitado cannot operate.
    assert _crear_reporte(equipo["inv"]).status_code == 403


def test_auxiliar_cannot_edit_others_or_old_reports(equipo) -> None:
    aux, aux2, enc = equipo["aux"], equipo["aux2"], equipo["enc"]
    rid = _crear_reporte(aux).json()["id"]
    cambio = {"turno": "M", "novedades": f"{PREFIX}editada"}

    assert (
        client.patch(
            f"{API}/reportes-turno/{rid}", json=cambio, headers=_auth(aux2)
        ).status_code
        == 403
    )
    assert (
        client.delete(f"{API}/reportes-turno/{rid}", headers=_auth(aux2)).status_code
        == 403
    )
    ok = client.patch(f"{API}/reportes-turno/{rid}", json=cambio, headers=_auth(aux))
    assert ok.status_code == 200, ok.text
    assert ok.json()["novedades"] == f"{PREFIX}editada"
    # Moving it to a shift the auxiliar may not close fails the WITH CHECK.
    moved = client.patch(
        f"{API}/reportes-turno/{rid}",
        json={"turno": "N", "novedades": None},
        headers=_auth(aux),
    )
    assert moved.status_code == 403

    viejo = _reporte_de_ayer(equipo["aux_perfil"])
    assert (
        client.patch(
            f"{API}/reportes-turno/{viejo}", json=cambio, headers=_auth(aux)
        ).status_code
        == 403
    )
    tareas = [{"descripcion": "Nueva tarea", "ambiente_id": None}]
    assert (
        client.put(
            f"{API}/reportes-turno/{viejo}/tareas", json=tareas, headers=_auth(aux)
        ).status_code
        == 403
    )
    assert (
        client.delete(f"{API}/reportes-turno/{viejo}", headers=_auth(aux)).status_code
        == 403
    )
    # Managers may edit any report.
    assert (
        client.patch(
            f"{API}/reportes-turno/{viejo}", json=cambio, headers=_auth(enc)
        ).status_code
        == 200
    )
    assert (
        client.delete(f"{API}/reportes-turno/{rid}", headers=_auth(aux)).status_code
        == 204
    )


def test_report_tasks_replace_and_mark_done(equipo) -> None:
    aux, aux2 = equipo["aux"], equipo["aux2"]
    r = _crear_reporte(
        aux,
        tareas=[
            {"descripcion": "Tarea uno", "ambiente_id": None},
            {"descripcion": "Tarea dos", "ambiente_id": None},
        ],
    )
    rid = r.json()["id"]
    tareas = {t["descripcion"]: t["id"] for t in r.json()["tareas"]}

    nuevas = [
        {
            "id": tareas["Tarea uno"],
            "descripcion": "Tarea uno bis",
            "ambiente_id": None,
        },
        {"descripcion": "Tarea tres", "ambiente_id": None},
    ]
    assert (
        client.put(
            f"{API}/reportes-turno/{rid}/tareas", json=nuevas, headers=_auth(aux2)
        ).status_code
        == 403
    )
    p = client.put(
        f"{API}/reportes-turno/{rid}/tareas", json=nuevas, headers=_auth(aux)
    )
    assert p.status_code == 200, p.text
    assert sorted(t["descripcion"] for t in p.json()) == ["Tarea tres", "Tarea uno bis"]

    pendientes = client.get(
        f"{API}/reporte-tareas/pendientes", headers=_auth(aux2)
    ).json()
    mias = [t for t in pendientes if t["reporte_id"] == rid]
    assert len(mias) == 2
    assert mias[0]["reporte"]["autor"]["nombre_completo"] == "Prueba Auxiliar"

    # Any operator may mark a task done (reporte_tareas_editar = fn_puede_operar).
    tid = mias[0]["id"]
    m = client.patch(
        f"{API}/reporte-tareas/{tid}", json={"hecha": True}, headers=_auth(aux2)
    )
    assert m.status_code == 200, m.text
    assert m.json()["hecha_por"] == equipo["aux2_perfil"]
    assert m.json()["hecha"] is True
    pendientes = client.get(
        f"{API}/reporte-tareas/pendientes", headers=_auth(aux)
    ).json()
    assert tid not in {t["id"] for t in pendientes}
    # A report with done tasks cannot be deleted (trigger) -> 422.
    assert (
        client.delete(f"{API}/reportes-turno/{rid}", headers=_auth(aux)).status_code
        == 422
    )


# --- fotos ---------------------------------------------------------------------


def test_photo_upload_validation(equipo, fotos_dir: Path) -> None:
    aux = equipo["aux"]
    rid = _crear_reporte(aux).json()["id"]
    url = f"{API}/reportes-turno/{rid}/foto"

    wrong = client.post(
        url, files={"foto": ("a.txt", b"hola", "text/plain")}, headers=_auth(aux)
    )
    assert wrong.status_code == 415
    big = client.post(
        url,
        files={"foto": ("a.png", b"\0" * (5 * 1024 * 1024 + 1), "image/png")},
        headers=_auth(aux),
    )
    assert big.status_code == 413
    broken = client.post(
        url, files={"foto": ("a.png", b"not an image", "image/png")}, headers=_auth(aux)
    )
    assert broken.status_code == 422
    other = client.post(
        url,
        files={"foto": ("a.png", _png(), "image/png")},
        headers=_auth(equipo["aux2"]),
    )
    assert other.status_code == 403
    assert not fotos_dir.exists() or not any(fotos_dir.rglob("*.*"))


def test_photo_lifecycle(equipo, fotos_dir: Path) -> None:
    aux, aux2, inv = equipo["aux"], equipo["aux2"], equipo["inv"]
    rid = _crear_reporte(aux).json()["id"]
    url = f"{API}/reportes-turno/{rid}/foto"

    up = client.post(
        url, files={"foto": ("../../x.png", _png(), "image/png")}, headers=_auth(aux)
    )
    assert up.status_code == 200, up.text
    foto_path = up.json()["foto_path"]
    assert up.json()["foto_expira"] is not None
    assert ".." not in foto_path and not foto_path.startswith("/")
    archivo = fotos_dir / foto_path
    assert archivo.is_file()

    assert client.get(url).status_code == 401
    assert client.get(url, headers=_auth(inv)).status_code == 403
    got = client.get(url, headers=_auth(aux2))
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/webp"

    assert client.delete(url, headers=_auth(aux2)).status_code == 403
    assert client.delete(url, headers=_auth(aux)).status_code == 204
    assert not archivo.exists()
    assert client.get(url, headers=_auth(aux)).status_code == 404

    # Deleting the report removes its photo too.
    up = client.post(
        url, files={"foto": ("a.png", _png(), "image/png")}, headers=_auth(aux)
    )
    archivo = fotos_dir / up.json()["foto_path"]
    assert archivo.is_file()
    assert (
        client.delete(f"{API}/reportes-turno/{rid}", headers=_auth(aux)).status_code
        == 204
    )
    assert not archivo.exists()


def test_expired_photos_are_cleaned(equipo, fotos_dir: Path) -> None:
    aux = equipo["aux"]
    rid = _crear_reporte(aux).json()["id"]
    up = client.post(
        f"{API}/reportes-turno/{rid}/foto",
        files={"foto": ("a.png", _png(), "image/png")},
        headers=_auth(aux),
    )
    archivo = fotos_dir / up.json()["foto_path"]
    with SessionLocal() as db:
        # trg_reportes_turno_foto keeps foto_expira unless foto_path changes.
        db.execute(text("set local session_replication_role = replica"))
        db.execute(
            text(
                "update horarios.reportes_turno set foto_expira = now() - interval '1 hour'"
                " where id = :id"
            ),
            {"id": rid},
        )
        db.commit()

    assert (
        client.post(
            f"{API}/reportes-turno/fotos/limpiar", headers=_auth(equipo["inv"])
        ).status_code
        == 403
    )
    r = client.post(f"{API}/reportes-turno/fotos/limpiar", headers=_auth(aux))
    assert r.status_code == 200, r.text
    assert r.json()["eliminadas"] >= 1
    assert not archivo.exists()
    with SessionLocal() as db:
        path = db.execute(
            text("select foto_path from horarios.reportes_turno where id = :id"),
            {"id": rid},
        ).scalar_one()
    assert path is None
