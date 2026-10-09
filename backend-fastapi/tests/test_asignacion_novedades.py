"""G5: lab novedades and shift-close (cierre) validation.

Ported from Django `novedades_vista` (tabs "novedades" and "cierres"):

- `horarios.novedades`: free-text notices of a shift, optionally tied to a lab
  and with an optional photo (stored on disk like the other horarios photos).
  They are listed for NOVEDADES_VIGENCIA_DIAS calendar days (La Paz), filtered
  by turno (M/MD/T/N) and lab. Read: fn_puede_ver; create: fn_puede_operar;
  delete: the author or fn_puede_gestionar_auxiliares.
- `horarios.reportes_turno` gains `estado` (pendiente/validado/rechazado),
  `validado_por` and `validado_en`. Only fn_puede_gestionar_auxiliares (Jefe,
  Encargado) decides, never on its own report, and only a pending one. Editing
  the content of a decided report sends it back to pendiente.
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
DOMAIN = "test-asignacion-nov.local"
PREFIX = "ZZNOV-"


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
    Image.new("RGB", (size, size), (30, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def _limpiar() -> None:
    with SessionLocal() as db:
        params = {"p": f"{PREFIX}%", "d": f"%@{DOMAIN}"}
        db.execute(text("delete from horarios.novedades where texto like :p"), params)
        db.execute(
            text(
                "delete from horarios.reportes_turno where novedades like :p or"
                " auxiliar_id in (select id from horarios.perfiles where correo like :d)"
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


@pytest.fixture
def fotos_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ASIGNACION_DATA_DIR", str(tmp_path))
    return tmp_path / "novedades"


@pytest.fixture
def horarios_restaurados() -> Iterator[None]:
    """Snapshot horarios_turno and restore it (shift M is moved to 00:00)."""
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
def equipo(make_usuario, horarios_restaurados) -> dict:
    """Two auxiliares on shift M since yesterday (M starts at 00:00, so
    fn_puede_cerrar_turno('M') holds), an encargado, a jefe, a tecnico, an
    invitado and one test lab."""
    aux, aux2 = make_usuario("Auxiliar"), make_usuario("Auxiliar")
    enc, jefe = make_usuario("Encargado"), make_usuario("Jefe")
    tec, inv = make_usuario("Tecnico"), make_usuario("Invitado")
    ids = {
        "aux_perfil": _perfil_id(aux),
        "aux2_perfil": _perfil_id(aux2),
        "enc_perfil": _perfil_id(enc),
    }
    with SessionLocal() as db:
        for key in ("aux_perfil", "aux2_perfil"):
            db.execute(
                text(
                    "insert into horarios.turnos_programados (perfil_id, turno, desde)"
                    " values (cast(:p as uuid), 'M', cast(:d as date))"
                ),
                {"p": ids[key], "d": _iso(-1)},
            )
        db.execute(
            text(
                "update horarios.horarios_turno set hora_inicio = '00:00'"
                " where turno = 'M'"
            )
        )
        lab = db.execute(
            text(
                "insert into horarios.ambientes (codigo, nombre)"
                " values (:c, 'Lab novedades') returning id"
            ),
            {"c": f"{PREFIX}{uuid4().hex[:6]}"},
        ).scalar_one()
        db.commit()
    return {
        "aux": aux,
        "aux2": aux2,
        "enc": enc,
        "jefe": jefe,
        "tec": tec,
        "inv": inv,
        "lab": int(lab),
        **ids,
    }


def _novedad(usuario: Usuario, texto: str = "aviso", foto: bytes | None = None, **form):
    files = {"foto": ("foto.png", foto, "image/png")} if foto is not None else None
    data = {"texto": f"{PREFIX}{texto}", **{k: str(v) for k, v in form.items()}}
    return client.post(
        f"{API}/novedades", data=data, files=files, headers=_auth(usuario)
    )


def _novedad_antigua(dias: int) -> int:
    with SessionLocal() as db:
        nid = db.execute(
            text(
                "insert into horarios.novedades (fecha, turno, texto)"
                " values (cast(:f as date), 'M', :t) returning id"
            ),
            {"f": _iso(-dias), "t": f"{PREFIX}hace {dias}"},
        ).scalar_one()
        db.commit()
    return int(nid)


def _crear_reporte(usuario: Usuario, turno: str = "M") -> dict:
    body = {"turno": turno, "novedades": f"{PREFIX}cierre", "tareas": []}
    r = client.post(f"{API}/reportes-turno", json=body, headers=_auth(usuario))
    assert r.status_code == 201, r.text
    return r.json()


def _decidir(usuario: Usuario, reporte_id: int, estado: str):
    return client.post(
        f"{API}/reportes-turno/{reporte_id}/validacion",
        json={"estado": estado},
        headers=_auth(usuario),
    )


# --- novedades -------------------------------------------------------------------


def test_novedad_with_photo_lab_and_turno(equipo, fotos_dir: Path) -> None:
    aux = equipo["aux"]
    r = _novedad(aux, "proyector", foto=_png(), turno="T", ambiente_id=equipo["lab"])
    assert r.status_code == 201, r.text
    nov = r.json()
    assert nov["turno"] == "T"
    assert nov["ambiente_id"] == equipo["lab"]
    assert nov["ambiente"]["codigo"].startswith(PREFIX)
    assert nov["autor"]["nombre_completo"] == "Prueba Auxiliar"
    assert nov["autor_id"] == equipo["aux_perfil"]
    assert nov["foto_path"]
    assert (fotos_dir / nov["foto_path"]).is_file()

    foto = client.get(f"{API}/novedades/{nov['id']}/foto", headers=_auth(aux))
    assert foto.status_code == 200
    assert foto.headers["content-type"] == "image/webp"

    # Without turno it takes the turno of the current hour; without lab, none.
    sin = _novedad(equipo["tec"], "general")
    assert sin.status_code == 201, sin.text
    assert sin.json()["turno"] in ("M", "MD", "T", "N")
    assert sin.json()["ambiente_id"] is None
    assert sin.json()["foto_path"] is None


def test_novedades_list_filters_and_permissions(equipo, fotos_dir: Path) -> None:
    aux, inv = equipo["aux"], equipo["inv"]
    uno = _novedad(aux, "uno", turno="T", ambiente_id=equipo["lab"]).json()["id"]
    dos = _novedad(aux, "dos", turno="N").json()["id"]

    def ids(**params) -> list[int]:
        r = client.get(f"{API}/novedades", params=params, headers=_auth(aux))
        assert r.status_code == 200, r.text
        return [n["id"] for n in r.json()]

    todas = ids()
    assert todas.index(dos) < todas.index(uno)  # newest first
    assert uno in ids(turno="T") and dos not in ids(turno="T")
    assert ids(ambiente_id=equipo["lab"]) == [uno]
    assert (
        client.get(
            f"{API}/novedades", params={"turno": "tarde"}, headers=_auth(aux)
        ).status_code
        == 422
    )

    assert client.get(f"{API}/novedades", headers=_auth(inv)).status_code == 403
    assert _novedad(inv, "no").status_code == 403


def test_novedades_show_for_three_days(equipo, fotos_dir: Path) -> None:
    vigente = _novedad_antigua(3)
    vencida = _novedad_antigua(4)
    r = client.get(f"{API}/novedades", headers=_auth(equipo["aux"]))
    listadas = [n["id"] for n in r.json()]
    assert vigente in listadas
    assert vencida not in listadas


def test_novedad_validation(equipo, fotos_dir: Path) -> None:
    aux = equipo["aux"]
    vacia = client.post(f"{API}/novedades", data={"texto": "   "}, headers=_auth(aux))
    assert vacia.status_code == 422
    assert _novedad(aux, turno="tarde").status_code == 422
    assert _novedad(aux, ambiente_id=999999999).status_code == 409
    mala = client.post(
        f"{API}/novedades",
        data={"texto": f"{PREFIX}mala"},
        files={"foto": ("x.txt", b"hola", "text/plain")},
        headers=_auth(aux),
    )
    assert mala.status_code == 415
    assert not fotos_dir.exists() or not any(fotos_dir.rglob("*.webp"))


def test_novedad_delete_by_author_or_manager(equipo, fotos_dir: Path) -> None:
    aux, aux2, enc = equipo["aux"], equipo["aux2"], equipo["enc"]
    propia = _novedad(aux, "propia", foto=_png()).json()
    ajena = _novedad(aux, "ajena").json()

    url = f"{API}/novedades/{propia['id']}"
    assert client.delete(url, headers=_auth(aux2)).status_code == 403
    assert client.delete(url, headers=_auth(aux)).status_code == 204
    assert not (fotos_dir / propia["foto_path"]).exists()
    assert client.delete(url, headers=_auth(aux)).status_code == 404

    otra = f"{API}/novedades/{ajena['id']}"
    assert client.delete(otra, headers=_auth(enc)).status_code == 204


# --- cierre validation -----------------------------------------------------------


def test_new_report_is_pending(equipo) -> None:
    rep = _crear_reporte(equipo["aux"])
    assert rep["estado"] == "pendiente"
    assert rep["validado_por"] is None
    assert rep["validado_en"] is None
    assert rep["validador"] is None


def test_manager_validates_but_not_the_author(equipo) -> None:
    aux, aux2, enc = equipo["aux"], equipo["aux2"], equipo["enc"]
    rid = _crear_reporte(aux)["id"]

    assert _decidir(aux, rid, "validado").status_code == 403  # author, no manager
    assert _decidir(aux2, rid, "validado").status_code == 403  # no manager
    assert _decidir(equipo["tec"], rid, "validado").status_code == 403
    assert _decidir(enc, rid, "aprobado").status_code == 422
    assert _decidir(enc, 999999999, "validado").status_code == 404

    r = _decidir(enc, rid, "validado")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["estado"] == "validado"
    assert rep["validado_por"] == equipo["enc_perfil"]
    assert rep["validado_en"] is not None
    assert rep["validador"]["nombre_completo"] == "Prueba Encargado"

    # Already decided.
    assert _decidir(equipo["jefe"], rid, "rechazado").status_code == 422

    pendientes = client.get(
        f"{API}/reportes-turno",
        params={"estado": "pendiente", "limite": 200},
        headers=_auth(enc),
    )
    assert pendientes.status_code == 200
    assert rid not in [x["id"] for x in pendientes.json()]
    validados = client.get(
        f"{API}/reportes-turno", params={"estado": "validado"}, headers=_auth(enc)
    ).json()
    assert rid in [x["id"] for x in validados]


def test_manager_cannot_validate_own_report(equipo) -> None:
    enc, jefe = equipo["enc"], equipo["jefe"]
    rid = _crear_reporte(enc)["id"]  # encargado closes his own turno
    r = _decidir(enc, rid, "validado")
    assert r.status_code == 403
    assert "propio" in r.json()["detail"]["message"]
    assert _decidir(jefe, rid, "rechazado").json()["estado"] == "rechazado"


def test_editing_a_decided_report_sends_it_back_to_pending(equipo) -> None:
    aux, enc = equipo["aux"], equipo["enc"]
    rid = _crear_reporte(aux)["id"]
    assert _decidir(enc, rid, "rechazado").json()["estado"] == "rechazado"

    r = client.patch(
        f"{API}/reportes-turno/{rid}",
        json={"turno": "M", "novedades": f"{PREFIX}corregido"},
        headers=_auth(aux),
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pendiente"
    assert r.json()["validado_por"] is None
    assert r.json()["validado_en"] is None


def test_estado_cannot_be_inconsistent() -> None:
    """validado_en is set exactly when the report was decided."""
    with SessionLocal() as db:
        with pytest.raises(Exception, match="reportes_turno_validacion_check"):
            db.execute(
                text(
                    "insert into horarios.reportes_turno (turno, novedades, estado)"
                    " values ('M', :n, 'validado')"
                ),
                {"n": f"{PREFIX}x"},
            )
        db.rollback()


# --- timeline --------------------------------------------------------------------


def test_timeline_shows_novedades_and_decisions(equipo, fotos_dir: Path) -> None:
    aux, enc = equipo["aux"], equipo["enc"]
    nov = _novedad(aux, "en timeline", foto=_png(), ambiente_id=equipo["lab"]).json()
    rid = _crear_reporte(aux)["id"]
    _decidir(enc, rid, "validado")

    r = client.get(f"{API}/timeline", headers=_auth(aux))
    assert r.status_code == 200, r.text
    eventos = r.json()["eventos"]
    ev_nov = next(
        e for e in eventos if e["evento"] == "novedad" and e["ref_id"] == nov["id"]
    )
    assert ev_nov["foto"] == "novedad"
    assert ev_nov["ambiente_id"] == equipo["lab"]
    assert ev_nov["autor"] == "Prueba Auxiliar"
    ev_cierre = next(
        e for e in eventos if e["evento"] == "cierre_validado" and e["ref_id"] == rid
    )
    assert ev_cierre["autor"] == "Prueba Encargado"
