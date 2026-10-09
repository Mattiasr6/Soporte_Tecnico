"""G7: software inventory and attention templates on the horarios schema.

Ported from Django `auxiliares/software/` and the per-PC software panel of
`auxiliares/laboratorios/<id>/pcs/` (Soporte tables Software, SoftwareLab,
PcSoftware and LabPlantillas) onto:

- `horarios.software`: catalogue (nombre, licencia gratuita/mixta/paga, uso,
  esencial, docentes, activo);
- `horarios.ambiente_software`: which software a lab has (lab x software matrix);
- `horarios.pc_software`: state of one software on one PC
  (instalado/falta/dañado, keyed by `ambiente_pcs.id`); a missing row reads as
  "falta". A change also records a `programas` attention on that PC, like
  Django recorded a LabAtencion;
- `horarios.plantillas_atencion`: prefilled lab attentions (nombre, tipo,
  descripcion, solucion, turno M/MD/T/N, activa).

Permissions: read fn_puede_ver; catalogue, matrix and templates
fn_puede_gestionar_auxiliares (Django `_gestiona_equipo`: Jefe/Encargado);
per-PC state fn_puede_operar (Django: any auxiliar of the roster).
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
DOMAIN = "test-asignacion-sw.local"
PREFIX = "ZZSW-"


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
        params = {"p": f"{PREFIX}%"}
        db.execute(
            text(
                "delete from horarios.atenciones where ambiente_id in"
                " (select id from horarios.ambientes where codigo like :p)"
            ),
            params,
        )
        db.execute(text("delete from horarios.software where nombre like :p"), params)
        db.execute(
            text("delete from horarios.plantillas_atencion where nombre like :p"),
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
def equipo(make_usuario) -> dict:
    """Roles plus one test lab with two PCs (the second one in mantenimiento)."""
    usuarios = {
        "jefe": make_usuario("Jefe"),
        "enc": make_usuario("Encargado"),
        "aux": make_usuario("Auxiliar"),
        "tec": make_usuario("Tecnico"),
        "dec": make_usuario("Decano"),
        "inv": make_usuario("Invitado"),
    }
    with SessionLocal() as db:
        lab = db.execute(
            text(
                "insert into horarios.ambientes (codigo, nombre)"
                " values (:c, 'Lab software') returning id"
            ),
            {"c": f"{PREFIX}{uuid4().hex[:6]}"},
        ).scalar_one()
        pc = db.execute(
            text(
                "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, orden)"
                " values (:a, 'PC-01', 0) returning id"
            ),
            {"a": lab},
        ).scalar_one()
        pc_mant = db.execute(
            text(
                "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, estado, orden)"
                " values (:a, 'PC-02', 'mantenimiento', 1) returning id"
            ),
            {"a": lab},
        ).scalar_one()
        db.commit()
    return {**usuarios, "lab": int(lab), "pc": int(pc), "pc_mant": int(pc_mant)}


def _software(usuario: Usuario, nombre: str = "Office", **campos) -> dict:
    body = {"nombre": f"{PREFIX}{nombre}", **campos}
    r = client.post(f"{API}/software", json=body, headers=_auth(usuario))
    assert r.status_code == 201, r.text
    return r.json()


# --- catalogue -------------------------------------------------------------------


def test_create_and_list_software_with_django_fields(equipo):
    sw = _software(
        equipo["jefe"],
        "Python",
        licencia="mixta",
        uso="Programación",
        esencial=True,
        docentes=True,
    )
    assert sw["nombre"] == f"{PREFIX}Python"
    assert sw["licencia"] == "mixta"
    assert sw["uso"] == "Programación"
    assert sw["esencial"] is True
    assert sw["docentes"] is True
    assert sw["activo"] is True
    assert sw["ambientes"] == []

    r = client.get(f"{API}/software", headers=_auth(equipo["aux"]))
    assert r.status_code == 200
    assert sw["id"] in [s["id"] for s in r.json()]


def test_software_defaults_and_validation(equipo):
    sw = _software(equipo["enc"], "Paint")
    assert sw["licencia"] == "gratuita"
    assert sw["uso"] == ""
    assert sw["esencial"] is False

    jefe = _auth(equipo["jefe"])
    dup = client.post(
        f"{API}/software", json={"nombre": f"  {PREFIX}paint "}, headers=jefe
    )
    assert dup.status_code == 409
    bad = client.post(
        f"{API}/software",
        json={"nombre": f"{PREFIX}X", "licencia": "pirata"},
        headers=jefe,
    )
    assert bad.status_code == 422
    vacio = client.post(f"{API}/software", json={"nombre": "  "}, headers=jefe)
    assert vacio.status_code == 422


def test_update_and_delete_software(equipo):
    jefe = _auth(equipo["jefe"])
    sw = _software(equipo["jefe"], "Gimp")
    body = {
        "nombre": f"{PREFIX}GIMP 2",
        "licencia": "gratuita",
        "uso": "Diseño",
        "esencial": False,
        "docentes": True,
        "activo": False,
    }
    r = client.put(f"{API}/software/{sw['id']}", json=body, headers=jefe)
    assert r.status_code == 200, r.text
    assert r.json()["nombre"] == f"{PREFIX}GIMP 2"
    assert r.json()["activo"] is False
    assert r.json()["docentes"] is True

    assert client.put(f"{API}/software/0", json=body, headers=jefe).status_code == 404
    assert client.delete(f"{API}/software/{sw['id']}", headers=jefe).status_code == 204
    assert client.delete(f"{API}/software/{sw['id']}", headers=jefe).status_code == 404


def test_catalogue_writes_need_gestionar(equipo):
    for rol in ("aux", "tec", "dec"):
        r = client.post(
            f"{API}/software",
            json={"nombre": f"{PREFIX}No"},
            headers=_auth(equipo[rol]),
        )
        assert r.status_code == 403, rol
    assert (
        client.get(f"{API}/software", headers=_auth(equipo["inv"])).status_code == 403
    )
    assert (
        client.get(f"{API}/software", headers=_auth(equipo["dec"])).status_code == 200
    )


# --- lab x software matrix -------------------------------------------------------


def test_lab_software_replace_and_read(equipo):
    a = _software(equipo["jefe"], "A")
    b = _software(equipo["jefe"], "B")
    lab = equipo["lab"]
    enc = _auth(equipo["enc"])

    r = client.put(
        f"{API}/ambientes/{lab}/software",
        json={"software_ids": [a["id"], b["id"], a["id"]]},
        headers=enc,
    )
    assert r.status_code == 200, r.text
    assert sorted(r.json()["software_ids"]) == sorted([a["id"], b["id"]])

    r = client.get(f"{API}/ambientes/{lab}/software", headers=_auth(equipo["aux"]))
    assert r.status_code == 200
    assert [s["nombre"] for s in r.json()] == [f"{PREFIX}A", f"{PREFIX}B"]

    lista = client.get(f"{API}/software", headers=enc).json()
    por_id = {s["id"]: s for s in lista}
    assert por_id[a["id"]]["ambientes"] == [lab]

    r = client.put(
        f"{API}/ambientes/{lab}/software", json={"software_ids": [b["id"]]}, headers=enc
    )
    assert r.json()["software_ids"] == [b["id"]]
    r = client.get(f"{API}/ambientes/{lab}/software", headers=enc)
    assert [s["id"] for s in r.json()] == [b["id"]]


def test_lab_software_errors_and_permission(equipo):
    a = _software(equipo["jefe"], "A")
    jefe = _auth(equipo["jefe"])
    lab = equipo["lab"]
    r = client.put(
        f"{API}/ambientes/{lab}/software", json={"software_ids": [0]}, headers=jefe
    )
    assert r.status_code == 422
    r = client.put(
        f"{API}/ambientes/0/software", json={"software_ids": [a["id"]]}, headers=jefe
    )
    assert r.status_code == 404
    r = client.put(
        f"{API}/ambientes/{lab}/software",
        json={"software_ids": [a["id"]]},
        headers=_auth(equipo["aux"]),
    )
    assert r.status_code == 403
    assert client.get(f"{API}/ambientes/0/software", headers=jefe).status_code == 404


# --- per-PC state ----------------------------------------------------------------


def _instalar(equipo, *nombres: str) -> list[dict]:
    sws = [_software(equipo["jefe"], n) for n in nombres]
    r = client.put(
        f"{API}/ambientes/{equipo['lab']}/software",
        json={"software_ids": [s["id"] for s in sws]},
        headers=_auth(equipo["jefe"]),
    )
    assert r.status_code == 200, r.text
    return sws


def test_pc_software_defaults_to_falta(equipo):
    (sw,) = _instalar(equipo, "Office")
    r = client.get(
        f"{API}/ambiente-pcs/{equipo['pc']}/software", headers=_auth(equipo["aux"])
    )
    assert r.status_code == 200
    assert r.json() == [
        {
            "software_id": sw["id"],
            "nombre": sw["nombre"],
            "estado": "falta",
            "actualizado_en": None,
            "actualizado_por": None,
        }
    ]
    r = client.get(f"{API}/ambiente-pcs/0/software", headers=_auth(equipo["aux"]))
    assert r.status_code == 404


def test_mark_pc_software_records_an_attention(equipo):
    (sw,) = _instalar(equipo, "Office")
    pc = equipo["pc"]
    aux = _auth(equipo["aux"])
    url = f"{API}/ambiente-pcs/{pc}/software/{sw['id']}"

    r = client.put(url, json={"estado": "instalado"}, headers=aux)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "instalado"
    assert cuerpo["atencion_id"] is not None

    with SessionLocal() as db:
        at = (
            db.execute(
                text(
                    "select tipo, ambiente_id, pc_id, descripcion, solucion, estado"
                    " from horarios.atenciones where id = :id"
                ),
                {"id": cuerpo["atencion_id"]},
            )
            .mappings()
            .one()
        )
    assert at["tipo"] == "programas"
    assert at["ambiente_id"] == equipo["lab"]
    assert at["pc_id"] == pc
    assert at["descripcion"] == f"{sw['nombre']} instalado en PC-01"
    assert at["solucion"] == "Instalación verificada en sala"
    assert at["estado"] == "resuelto"

    estados = client.get(f"{API}/ambiente-pcs/{pc}/software", headers=aux).json()
    assert estados[0]["estado"] == "instalado"
    assert estados[0]["actualizado_por"] == "Prueba Auxiliar"
    assert estados[0]["actualizado_en"] is not None

    # Same estado again: nothing changes and no new attention.
    r = client.put(url, json={"estado": "instalado"}, headers=aux)
    assert r.status_code == 200
    assert r.json()["atencion_id"] is None

    r = client.put(url, json={"estado": "dañado"}, headers=_auth(equipo["tec"]))
    assert r.status_code == 200
    with SessionLocal() as db:
        at = (
            db.execute(
                text(
                    "select descripcion, estado from horarios.atenciones where id = :id"
                ),
                {"id": r.json()["atencion_id"]},
            )
            .mappings()
            .one()
        )
    assert at["descripcion"] == f"{sw['nombre']} dañado en PC-01"
    assert at["estado"] == "pendiente"


def test_mark_pc_software_rules(equipo):
    (sw,) = _instalar(equipo, "Office")
    otro = _software(equipo["jefe"], "Fuera")
    aux = _auth(equipo["aux"])
    pc = equipo["pc"]

    bad = client.put(
        f"{API}/ambiente-pcs/{pc}/software/{sw['id']}",
        json={"estado": "roto"},
        headers=aux,
    )
    assert bad.status_code == 422
    fuera = client.put(
        f"{API}/ambiente-pcs/{pc}/software/{otro['id']}",
        json={"estado": "instalado"},
        headers=aux,
    )
    assert fuera.status_code == 422
    sin_pc = client.put(
        f"{API}/ambiente-pcs/0/software/{sw['id']}",
        json={"estado": "instalado"},
        headers=aux,
    )
    assert sin_pc.status_code == 404
    # The attention trigger only allows correctivo on a PC that is not operativa.
    mant = client.put(
        f"{API}/ambiente-pcs/{equipo['pc_mant']}/software/{sw['id']}",
        json={"estado": "instalado"},
        headers=aux,
    )
    assert mant.status_code == 422
    with SessionLocal() as db:
        n = db.execute(
            text("select count(*) from horarios.pc_software where pc_id = :p"),
            {"p": equipo["pc_mant"]},
        ).scalar_one()
    assert n == 0
    dec = client.put(
        f"{API}/ambiente-pcs/{pc}/software/{sw['id']}",
        json={"estado": "instalado"},
        headers=_auth(equipo["dec"]),
    )
    assert dec.status_code == 403


def test_removing_software_from_lab_drops_pc_states(equipo):
    (sw,) = _instalar(equipo, "Office")
    url = f"{API}/ambiente-pcs/{equipo['pc']}/software/{sw['id']}"
    assert (
        client.put(
            url, json={"estado": "falta"}, headers=_auth(equipo["aux"])
        ).status_code
        == 200
    )
    r = client.put(
        f"{API}/ambientes/{equipo['lab']}/software",
        json={"software_ids": []},
        headers=_auth(equipo["jefe"]),
    )
    assert r.status_code == 200
    with SessionLocal() as db:
        n = db.execute(
            text("select count(*) from horarios.pc_software where pc_id = :p"),
            {"p": equipo["pc"]},
        ).scalar_one()
    assert n == 0


# --- attention templates -----------------------------------------------------------


def test_templates_crud(equipo):
    enc = _auth(equipo["enc"])
    body = {
        "nombre": f"{PREFIX}Instalar Office",
        "tipo": "programas",
        "descripcion": "Instalación de Office",
        "solucion": "Instalado y activado",
        "turno": "MD",
    }
    r = client.post(f"{API}/plantillas-atencion", json=body, headers=enc)
    assert r.status_code == 201, r.text
    pl = r.json()
    assert pl["tipo"] == "programas"
    assert pl["turno"] == "MD"
    assert pl["activa"] is True

    lista = client.get(f"{API}/plantillas-atencion", headers=_auth(equipo["aux"]))
    assert lista.status_code == 200
    assert pl["id"] in [p["id"] for p in lista.json()]

    cambio = {**body, "turno": None, "activa": False, "tipo": "preventivo"}
    r = client.put(f"{API}/plantillas-atencion/{pl['id']}", json=cambio, headers=enc)
    assert r.status_code == 200, r.text
    assert r.json()["turno"] is None
    assert r.json()["activa"] is False
    assert r.json()["tipo"] == "preventivo"

    activas = client.get(
        f"{API}/plantillas-atencion", params={"activas": "true"}, headers=enc
    ).json()
    assert pl["id"] not in [p["id"] for p in activas]

    assert (
        client.delete(f"{API}/plantillas-atencion/{pl['id']}", headers=enc).status_code
        == 204
    )
    assert (
        client.delete(f"{API}/plantillas-atencion/{pl['id']}", headers=enc).status_code
        == 404
    )


def test_template_validation_and_permission(equipo):
    jefe = _auth(equipo["jefe"])
    base = {"nombre": f"{PREFIX}T", "descripcion": "Algo"}
    for campo, valor in (("turno", "mañana"), ("tipo", "correctivo"), ("tipo", "x")):
        r = client.post(
            f"{API}/plantillas-atencion", json={**base, campo: valor}, headers=jefe
        )
        assert r.status_code == 422, (campo, valor)
    r = client.post(
        f"{API}/plantillas-atencion", json={**base, "nombre": " "}, headers=jefe
    )
    assert r.status_code == 422
    r = client.post(
        f"{API}/plantillas-atencion", json=base, headers=_auth(equipo["aux"])
    )
    assert r.status_code == 403
    assert (
        client.get(
            f"{API}/plantillas-atencion", headers=_auth(equipo["inv"])
        ).status_code
        == 403
    )
