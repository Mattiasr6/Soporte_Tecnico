"""G6: Saturday planner and schedule export.

Ported from Django `auxiliares/horarios-sabados/` and
`auxiliares/horarios/export.xlsx|.pdf`:

- `horarios.sabados` is one planned Saturday (date + note); clearing a date
  deletes it with its assignments and hour overrides.
- `horarios.rotacion_sabados` now holds one row per date and auxiliar (turno
  M/MD/T), so a turno can have several auxiliares.
- `horarios.sabado_horarios` keeps optional per-date hours of a turno; without
  one the turno uses `horarios_turno`.
- Read: fn_puede_ver; plan/clear: fn_puede_gestionar_auxiliares.
- Export (XLSX/PDF) of the weekly shifts (vigente turno of every active
  auxiliar/encargado) and of the Saturdays of a month (plus "Libre" rows).
Every row the tests create is removed at teardown.
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
DOMAIN = "test-asignacion-sab.local"
PREFIX = "ZZSAB-"
# Far-future month, so real plans are never touched: Saturdays 3..31.
ANIO, MES = 2035, 3
SABADOS = ["2035-03-03", "2035-03-10", "2035-03-17", "2035-03-24", "2035-03-31"]
SABADO = SABADOS[1]
MES_PARAMS = {"mes": MES, "anio": ANIO}


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


def _limpiar() -> None:
    with SessionLocal() as db:
        db.execute(
            text("delete from horarios.sabados where fecha = any(cast(:f as date[]))"),
            {"f": SABADOS},
        )
        db.execute(
            text(
                "delete from horarios.turnos_programados where perfil_id in"
                " (select id from horarios.perfiles where correo like :d)"
            ),
            {"d": f"%@{DOMAIN}"},
        )
        db.commit()


@pytest.fixture
def make_usuario() -> Iterator[Callable[[str], Usuario]]:
    created: list[int] = []

    def _make(role: str) -> Usuario:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            usuario = Usuario(
                email=f"{uuid4().hex[:10]}@{DOMAIN}",
                display_name=f"{PREFIX}{role} {uuid4().hex[:6]}",
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


def _defaults(usuario: Usuario) -> dict[str, tuple[str, str]]:
    lista = client.get(f"{API}/horarios-turno", headers=_auth(usuario)).json()
    return {h["turno"]: (h["hora_inicio"], h["hora_fin"]) for h in lista}


def _dia(usuario: Usuario, fecha: str) -> dict:
    r = client.get(f"{API}/sabados", params=MES_PARAMS, headers=_auth(usuario))
    assert r.status_code == 200, r.text
    return next(s for s in r.json()["sabados"] if s["fecha"] == fecha)


def _turno(dia: dict, turno: str) -> dict:
    return next(t for t in dia["turnos"] if t["turno"] == turno)


# --- auth ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/sabados"],
)
def test_reads_need_token_and_staff(make_usuario, path: str) -> None:
    assert client.get(f"{API}{path}").status_code == 401
    r = client.get(f"{API}{path}", headers=_auth(make_usuario("Auxiliar")))
    assert r.status_code == 200, r.text
    invitado = make_usuario("Invitado")
    assert client.get(f"{API}{path}", headers=_auth(invitado)).status_code == 403


# --- planner --------------------------------------------------------------------


def test_month_lists_every_saturday_with_default_hours(make_usuario) -> None:
    aux = make_usuario("Auxiliar")
    r = client.get(f"{API}/sabados", params=MES_PARAMS, headers=_auth(aux))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["mes"], body["anio"]) == (MES, ANIO)
    assert [s["fecha"] for s in body["sabados"]] == SABADOS
    defaults = _defaults(aux)
    assert [
        (h["turno"], h["hora_inicio"], h["hora_fin"]) for h in body["horarios"]
    ] == [(t, *defaults[t]) for t in ("M", "MD", "T")]
    for dia in body["sabados"]:
        assert dia["planificado"] is False
        assert dia["nota"] is None
        assert [t["turno"] for t in dia["turnos"]] == ["M", "MD", "T"]
        for t in dia["turnos"]:
            assert t["auxiliares"] == []
            assert t["personalizado"] is False
            assert (t["hora_inicio"], t["hora_fin"]) == defaults[t["turno"]]

    assert (
        client.get(
            f"{API}/sabados", params={"mes": 13, "anio": ANIO}, headers=_auth(aux)
        ).status_code
        == 422
    )


def test_plan_saturday_with_several_auxiliares_and_custom_hours(make_usuario) -> None:
    a1, a2, a3 = (make_usuario("Auxiliar") for _ in range(3))
    enc = make_usuario("Encargado")
    p1, p2, p3 = (_perfil_id(u) for u in (a1, a2, a3))
    body = {
        "nota": "Feria",
        "turnos": [
            {
                "turno": "M",
                "hora_inicio": "08:00",
                "hora_fin": "12:30",
                "auxiliares": [p1, p2],
            },
            {"turno": "T", "auxiliares": [p3]},
        ],
    }
    url = f"{API}/sabados/{SABADO}"
    assert client.put(url, json=body, headers=_auth(a1)).status_code == 403

    r = client.put(url, json=body, headers=_auth(enc))
    assert r.status_code == 200, r.text
    dia = r.json()
    assert dia["fecha"] == SABADO
    assert dia["planificado"] is True
    assert dia["nota"] == "Feria"
    m = _turno(dia, "M")
    assert (m["hora_inicio"], m["hora_fin"]) == ("08:00:00", "12:30:00")
    assert m["personalizado"] is True
    assert {a["id"] for a in m["auxiliares"]} == {p1, p2}
    assert all(a["nombre_completo"].startswith(PREFIX) for a in m["auxiliares"])
    t = _turno(dia, "T")
    assert t["personalizado"] is False
    assert (t["hora_inicio"], t["hora_fin"]) == _defaults(enc)["T"]
    assert [a["id"] for a in t["auxiliares"]] == [p3]
    assert _turno(dia, "MD")["auxiliares"] == []

    # The month view (any staff) shows the same plan.
    assert _dia(a1, SABADO) == dia
    assert _dia(a1, SABADOS[0])["planificado"] is False


def test_replanning_replaces_and_clearing_removes_the_date(make_usuario) -> None:
    a1, a2 = make_usuario("Auxiliar"), make_usuario("Auxiliar")
    enc = make_usuario("Encargado")
    p1, p2 = _perfil_id(a1), _perfil_id(a2)
    url = f"{API}/sabados/{SABADO}"
    first = {
        "turnos": [
            {
                "turno": "M",
                "hora_inicio": "08:00",
                "hora_fin": "11:00",
                "auxiliares": [p1, p2],
            }
        ]
    }
    assert client.put(url, json=first, headers=_auth(enc)).status_code == 200

    # A new PUT replaces the whole date: M empties and its custom hours go.
    second = {"turnos": [{"turno": "MD", "auxiliares": [p1]}]}
    dia = client.put(url, json=second, headers=_auth(enc)).json()
    assert _turno(dia, "M")["auxiliares"] == []
    assert _turno(dia, "M")["personalizado"] is False
    assert [a["id"] for a in _turno(dia, "MD")["auxiliares"]] == [p1]
    assert dia["nota"] is None

    # Custom hours equal to the defaults are not kept as an override.
    md = _defaults(enc)["MD"]
    same = {
        "turnos": [
            {
                "turno": "MD",
                "hora_inicio": md[0],
                "hora_fin": md[1],
                "auxiliares": [p1],
            }
        ]
    }
    dia = client.put(url, json=same, headers=_auth(enc)).json()
    assert _turno(dia, "MD")["personalizado"] is False

    assert client.delete(url, headers=_auth(a1)).status_code == 403
    assert client.delete(url, headers=_auth(enc)).status_code == 204
    assert _dia(enc, SABADO)["planificado"] is False
    assert client.delete(url, headers=_auth(enc)).status_code == 404

    # Saving a date with nobody on it clears it too (Django behaviour).
    assert client.put(url, json=first, headers=_auth(enc)).status_code == 200
    vacio = client.put(url, json={"turnos": []}, headers=_auth(enc))
    assert vacio.status_code == 200, vacio.text
    assert vacio.json()["planificado"] is False
    assert _dia(enc, SABADO)["planificado"] is False


@pytest.mark.parametrize(
    ("fecha", "turnos"),
    [
        # Not a Saturday.
        ("2035-03-11", [{"turno": "M", "auxiliares": ["AUX"]}]),
        # Same auxiliar in two turnos of one day.
        (
            SABADO,
            [
                {"turno": "M", "auxiliares": ["AUX"]},
                {"turno": "T", "auxiliares": ["AUX"]},
            ],
        ),
        # The same turno twice.
        (
            SABADO,
            [{"turno": "M", "auxiliares": ["AUX"]}, {"turno": "M", "auxiliares": []}],
        ),
        # Only one of the two hours.
        (SABADO, [{"turno": "M", "hora_inicio": "08:00", "auxiliares": ["AUX"]}]),
        # End before start.
        (
            SABADO,
            [
                {
                    "turno": "M",
                    "hora_inicio": "12:00",
                    "hora_fin": "08:00",
                    "auxiliares": ["AUX"],
                }
            ],
        ),
        # Saturdays have no night shift.
        (SABADO, [{"turno": "N", "auxiliares": ["AUX"]}]),
        # Unknown perfil.
        (SABADO, [{"turno": "M", "auxiliares": [str(uuid4())]}]),
    ],
)
def test_invalid_plans_are_rejected(make_usuario, fecha: str, turnos: list) -> None:
    aux, enc = make_usuario("Auxiliar"), make_usuario("Encargado")
    pid = _perfil_id(aux)
    for t in turnos:
        t["auxiliares"] = [pid if a == "AUX" else a for a in t["auxiliares"]]
    r = client.put(
        f"{API}/sabados/{fecha}", json={"turnos": turnos}, headers=_auth(enc)
    )
    assert r.status_code == 422, r.text
    assert _dia(enc, SABADO)["planificado"] is False


def test_deleting_a_perfil_drops_its_saturdays(make_usuario) -> None:
    a1, a2 = make_usuario("Auxiliar"), make_usuario("Auxiliar")
    enc = make_usuario("Encargado")
    p1, p2 = _perfil_id(a1), _perfil_id(a2)
    body = {"turnos": [{"turno": "M", "auxiliares": [p1, p2]}]}
    assert (
        client.put(f"{API}/sabados/{SABADO}", json=body, headers=_auth(enc)).status_code
        == 200
    )
    with SessionLocal() as db:
        db.execute(text("delete from horarios.perfiles where id = :id"), {"id": p2})
        db.commit()
    m = _turno(_dia(enc, SABADO), "M")
    assert [a["id"] for a in m["auxiliares"]] == [p1]
