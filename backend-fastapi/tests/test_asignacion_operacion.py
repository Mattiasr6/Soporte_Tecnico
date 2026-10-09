"""T6b: auxiliar operation of the asignacion module.

Tables atenciones, fallas_pc, solicitudes_baja and objetos_perdidos (+ the old
Supabase bucket `objetos-perdidos`) plus rpc_cambiar_estado_pcs,
rpc_registrar_reparaciones, rpc_resolver_baja, fn_generar_pcs and
fn_limpiar_fotos_objetos.

Old RLS rules (99_rls_reference.sql) enforced by the API:
- read everything here: fn_puede_ver (invitado -> 403);
- atenciones create/update/delete, objetos_perdidos create/update: fn_puede_operar;
- fallas_pc write, objetos_perdidos delete, solicitudes_baja resolve/delete:
  fn_puede_gestionar_auxiliares (auxiliar -> 403);
- solicitudes_baja create: fn_puede_operar() and estado = 'pendiente';
- a PC state only changes through rpc_cambiar_estado_pcs/rpc_registrar_reparaciones
  (trigger fn_trg_pc_estado_controlado).
Every row the tests create is tagged and removed at teardown; photos go to a
temporary directory, never to the real data dir.
"""

import io
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
DOMAIN = "test-asignacion-op.local"
PREFIX = "ZZOP-"


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


def _cleanup() -> None:
    labs = "select id from horarios.ambientes where codigo like :p"
    params = {"p": f"{PREFIX}%"}
    with SessionLocal() as db:
        db.execute(
            text(
                "delete from horarios.solicitudes_baja where pc_id in "
                f"(select id from horarios.ambiente_pcs where ambiente_id in ({labs}))"
            ),
            params,
        )
        for table in ("atenciones", "objetos_perdidos", "ambiente_pcs"):
            db.execute(
                text(f"delete from horarios.{table} where ambiente_id in ({labs})"),
                params,
            )
        db.execute(text("delete from horarios.ambientes where codigo like :p"), params)
        db.execute(text("delete from horarios.fallas_pc where nombre like :p"), params)
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
def fotos_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ASIGNACION_DATA_DIR", str(tmp_path))
    return tmp_path / "objetos-perdidos"


@pytest.fixture
def lab(make_usuario) -> dict:
    """A test laboratory with two active PCs, plus auxiliar/encargado/invitado."""
    with SessionLocal() as db:
        lab_id = db.execute(
            text(
                "insert into horarios.ambientes (codigo, nombre)"
                " values (:c, 'Lab de prueba') returning id"
            ),
            {"c": f"{PREFIX}{uuid4().hex[:6]}"},
        ).scalar_one()
        pcs = [
            db.execute(
                text(
                    "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, orden)"
                    " values (:a, :e, :o) returning id"
                ),
                {"a": lab_id, "e": f"PC-{n}", "o": n},
            ).scalar_one()
            for n in (1, 2)
        ]
        db.commit()
    return {
        "id": lab_id,
        "pcs": pcs,
        "aux": make_usuario("Auxiliar"),
        "enc": make_usuario("Encargado"),
        "inv": make_usuario("Invitado"),
    }


def _pc_estado(pc_id: int) -> str:
    with SessionLocal() as db:
        return db.execute(
            text("select estado from horarios.ambiente_pcs where id = :id"),
            {"id": pc_id},
        ).scalar_one()


def _ticket(lab: dict, **extra) -> dict:
    return {
        "ambiente_id": lab["id"],
        "tipo": "docente",
        "descripcion": f"{PREFIX}no prende el proyector",
        "estado": "pendiente",
        **extra,
    }


# --- auth ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/atenciones",
        "/atenciones/arrastradas",
        "/fallas-pc",
        "/solicitudes-baja",
        "/objetos-perdidos",
        "/ambiente-pcs/mis-bajas?desde=2026-01-01T00:00:00-04:00",
    ],
)
def test_reads_need_token_and_staff(make_usuario, path: str) -> None:
    assert client.get(f"{API}{path}").status_code == 401
    r = client.get(f"{API}{path}", headers=_auth(make_usuario("Auxiliar")))
    assert r.status_code == 200, r.text
    invitado = make_usuario("Invitado")
    assert client.get(f"{API}{path}", headers=_auth(invitado)).status_code == 403


# --- atenciones ------------------------------------------------------------------


def test_auxiliar_creates_edits_and_deletes_tickets(lab) -> None:
    aux, inv = lab["aux"], lab["inv"]
    pid = _perfil_id(aux)
    body = [_ticket(lab, pc_id=lab["pcs"][0]), _ticket(lab, pc_id=lab["pcs"][1])]

    assert client.post(f"{API}/atenciones", json=body).status_code == 401
    assert (
        client.post(f"{API}/atenciones", json=body, headers=_auth(inv)).status_code
        == 403
    )
    r = client.post(f"{API}/atenciones", json=body, headers=_auth(aux))
    assert r.status_code == 201, r.text
    creados = r.json()
    assert sorted(c["pc_id"] for c in creados) == sorted(lab["pcs"])
    ids = [c["id"] for c in creados]

    # Unknown / read-only columns are rejected.
    bad = [_ticket(lab, creado_en="2020-01-01T00:00:00Z")]
    assert (
        client.post(f"{API}/atenciones", json=bad, headers=_auth(aux)).status_code
        == 422
    )

    # Pending tickets are carried over (pase de turno) with their embeds.
    arr = client.get(f"{API}/atenciones/arrastradas", headers=_auth(aux)).json()
    mios = [a for a in arr if a["id"] in ids]
    assert len(mios) == 2
    assert mios[0]["ambiente"]["codigo"].startswith(PREFIX)
    assert mios[0]["pc"]["etiqueta"].startswith("PC-")
    assert mios[0]["autor"]["nombre_completo"]
    assert mios[0]["auxiliar_id"] == pid

    # Bulk update (state change of a lote) and single update.
    cambios = {"estado": "resuelto", "resuelto_por": pid, "solucion": "cable"}
    r = client.patch(
        f"{API}/atenciones",
        json={"ids": ids, "cambios": cambios},
        headers=_auth(aux),
    )
    assert r.status_code == 200, r.text
    assert r.json()["actualizadas"] == 2
    denied = client.patch(
        f"{API}/atenciones", json={"ids": ids, "cambios": cambios}, headers=_auth(inv)
    )
    assert denied.status_code == 403
    r = client.patch(
        f"{API}/atenciones/{ids[0]}", json={"prioridad": 1}, headers=_auth(aux)
    )
    assert r.status_code == 200, r.text
    assert r.json()["prioridad"] == 1
    # DB checks still apply (prioridad 1..3).
    r = client.patch(
        f"{API}/atenciones/{ids[0]}", json={"prioridad": 9}, headers=_auth(aux)
    )
    assert r.status_code == 422

    # Filters: participante (author or collaborator) and ambiente.
    lista = client.get(
        f"{API}/atenciones",
        params={"participante": pid, "ambiente_id": lab["id"], "estado": "resuelto"},
        headers=_auth(lab["enc"]),
    ).json()
    assert {a["id"] for a in lista} == set(ids)
    arr = client.get(f"{API}/atenciones/arrastradas", headers=_auth(aux)).json()
    assert not [a for a in arr if a["id"] in ids]

    query = "&".join(f"id={i}" for i in ids)
    assert (
        client.delete(f"{API}/atenciones?{query}", headers=_auth(inv)).status_code
        == 403
    )
    assert (
        client.delete(f"{API}/atenciones?{query}", headers=_auth(aux)).status_code
        == 204
    )
    lista = client.get(
        f"{API}/atenciones", params={"ambiente_id": lab["id"]}, headers=_auth(aux)
    ).json()
    assert lista == []


# --- estado de PCs ---------------------------------------------------------------


def test_pc_state_changes_only_through_the_rpc(lab) -> None:
    aux, inv = lab["aux"], lab["inv"]
    pc = lab["pcs"][0]

    # A direct update of the state is refused by the DB trigger.
    r = client.patch(
        f"{API}/ambiente-pcs/{pc}", json={"estado": "inactiva"}, headers=_auth(aux)
    )
    assert r.status_code in (422, 403), r.text
    assert _pc_estado(pc) == "operativa"

    body = {"ids": [pc], "estado": "inactiva", "detalle": "sin teclado"}
    assert client.post(f"{API}/ambiente-pcs/estado", json=body).status_code == 401
    assert (
        client.post(
            f"{API}/ambiente-pcs/estado", json=body, headers=_auth(inv)
        ).status_code
        == 403
    )
    r = client.post(f"{API}/ambiente-pcs/estado", json=body, headers=_auth(aux))
    assert r.status_code == 200, r.text
    assert r.json()["cambiadas"] == 1
    assert _pc_estado(pc) == "inactiva"
    tickets = client.get(
        f"{API}/atenciones", params={"ambiente_id": lab["id"]}, headers=_auth(aux)
    ).json()
    assert [t["tipo"] for t in tickets] == ["cambio_estado"]

    # The RPC's own validation comes back as 422 with its message.
    body["detalle"] = "x"
    r = client.post(f"{API}/ambiente-pcs/estado", json=body, headers=_auth(aux))
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "P0001"


def test_tecnico_operates_like_auxiliar_but_does_not_manage(lab, make_usuario) -> None:
    """0023: a Soporte Tecnico gets OPERAR (tickets, PC states), not EDITAR/GESTIONAR."""
    tec = make_usuario("Tecnico")
    pc = lab["pcs"][1]
    r = client.get(f"{API}/atenciones", headers=_auth(tec))
    assert r.status_code == 200, r.text
    r = client.post(
        f"{API}/atenciones", json=[_ticket(lab, pc_id=pc)], headers=_auth(tec)
    )
    assert r.status_code == 201, r.text
    body = {"ids": [pc], "estado": "inactiva", "detalle": "sin teclado"}
    r = client.post(f"{API}/ambiente-pcs/estado", json=body, headers=_auth(tec))
    assert r.status_code == 200, r.text
    assert _pc_estado(pc) == "inactiva"

    # GESTIONAR_AUXILIARES and EDITAR stay out of reach.
    r = client.post(
        f"{API}/fallas-pc", json={"nombre": f"{PREFIX}falla"}, headers=_auth(tec)
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "42501"
    r = client.put(
        f"{API}/feriados/2099-12-24",
        json={"descripcion": f"{PREFIX}feriado"},
        headers=_auth(tec),
    )
    assert r.status_code == 403, r.text


def test_generar_pcs(lab) -> None:
    url = f"{API}/ambientes/{lab['id']}/pcs/generar"
    assert (
        client.post(url, json={"cantidad": 2}, headers=_auth(lab["inv"])).status_code
        == 403
    )
    r = client.post(url, json={"cantidad": 2}, headers=_auth(lab["aux"]))
    assert r.status_code == 200, r.text
    assert r.json()["creadas"] == 2


# --- fichas de reparación ----------------------------------------------------------


def test_fallas_catalog_and_repairs(lab) -> None:
    aux, enc, inv = lab["aux"], lab["enc"], lab["inv"]
    falla = {"nombre": f"{PREFIX}fuente", "categoria": "hardware", "orden": 1}
    assert (
        client.post(f"{API}/fallas-pc", json=falla, headers=_auth(aux)).status_code
        == 403
    )
    r = client.post(f"{API}/fallas-pc", json=falla, headers=_auth(enc))
    assert r.status_code == 201, r.text
    falla_id = r.json()["id"]
    r = client.patch(
        f"{API}/fallas-pc/{falla_id}", json={"activo": False}, headers=_auth(enc)
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    assert (
        client.patch(
            f"{API}/fallas-pc/{falla_id}", json={"activo": True}, headers=_auth(aux)
        ).status_code
        == 403
    )
    nombres = [
        f["nombre"] for f in client.get(f"{API}/fallas-pc", headers=_auth(aux)).json()
    ]
    assert falla["nombre"] in nombres

    ficha = {
        "pc_id": lab["pcs"][1],
        "fallas": [falla_id],
        "falla_otra": "",
        "diagnostico": "no enciende",
        "correccion": "",
        "pieza": "",
        "estado_final": "mantenimiento",
    }
    body = {"fichas": [ficha], "colaboradores": [], "prioridad": 2}
    assert (
        client.post(f"{API}/reparaciones", json=body, headers=_auth(inv)).status_code
        == 403
    )
    r = client.post(f"{API}/reparaciones", json=body, headers=_auth(aux))
    assert r.status_code == 200, r.text
    assert r.json()["registradas"] == 1
    assert _pc_estado(lab["pcs"][1]) == "mantenimiento"
    # Left in maintenance: the ticket stays open and is carried over.
    arr = client.get(f"{API}/atenciones/arrastradas", headers=_auth(aux)).json()
    assert [a["tipo"] for a in arr if a["pc_id"] == lab["pcs"][1]] == ["correctivo"]


# --- solicitudes de baja -----------------------------------------------------------


def test_baja_requests_are_pending_and_resolved_by_managers(lab) -> None:
    aux, enc, inv = lab["aux"], lab["enc"], lab["inv"]
    pc1, pc2 = lab["pcs"]

    forced = [{"pc_id": pc1, "motivo": "placa quemada", "estado": "aprobada"}]
    r = client.post(f"{API}/solicitudes-baja", json=forced, headers=_auth(aux))
    assert r.status_code == 422
    body = [
        {"pc_id": pc1, "motivo": "placa quemada"},
        {"pc_id": pc2, "motivo": "vieja"},
    ]
    assert (
        client.post(
            f"{API}/solicitudes-baja", json=body, headers=_auth(inv)
        ).status_code
        == 403
    )
    r = client.post(f"{API}/solicitudes-baja", json=body, headers=_auth(aux))
    assert r.status_code == 201, r.text

    pendientes = [
        s
        for s in client.get(f"{API}/solicitudes-baja", headers=_auth(aux)).json()
        if s["pc_id"] in (pc1, pc2)
    ]
    assert {s["estado"] for s in pendientes} == {"pendiente"}
    assert pendientes[0]["pc"]["ambiente"]["codigo"].startswith(PREFIX)
    assert pendientes[0]["autor"]["nombre_completo"]
    por_pc = {s["pc_id"]: s["id"] for s in pendientes}

    resolver = f"{API}/solicitudes-baja/{por_pc[pc1]}/resolver"
    assert (
        client.post(
            resolver, json={"aprobar": True, "respuesta": None}, headers=_auth(aux)
        ).status_code
        == 403
    )
    r = client.post(
        resolver, json={"aprobar": True, "respuesta": None}, headers=_auth(enc)
    )
    assert r.status_code == 200, r.text
    assert _pc_estado(pc1) == "baja"

    # Rejecting needs a reason (RPC rule -> 422), then works.
    rechazar = f"{API}/solicitudes-baja/{por_pc[pc2]}/resolver"
    r = client.post(
        rechazar, json={"aprobar": False, "respuesta": ""}, headers=_auth(enc)
    )
    assert r.status_code == 422
    r = client.post(
        rechazar, json={"aprobar": False, "respuesta": "se repara"}, headers=_auth(enc)
    )
    assert r.status_code == 200, r.text
    assert _pc_estado(pc2) == "operativa"
    restantes = client.get(f"{API}/solicitudes-baja", headers=_auth(aux)).json()
    assert not [s for s in restantes if s["pc_id"] in (pc1, pc2)]

    # The encargado gave pc1 de baja: it shows in his shift closing.
    def mis_bajas(usuario: Usuario) -> list[str]:
        r = client.get(
            f"{API}/ambiente-pcs/mis-bajas",
            params={"desde": "2000-01-01T00:00:00-04:00"},
            headers=_auth(usuario),
        )
        assert r.status_code == 200, r.text
        return [
            b["etiqueta"]
            for b in r.json()
            if (b["ambiente"] or {}).get("codigo", "").startswith(PREFIX)
        ]

    assert mis_bajas(enc) == ["PC-1"]
    assert mis_bajas(aux) == []


# --- objetos perdidos ---------------------------------------------------------------


def _registrar(lab: dict, usuario: Usuario, foto: bytes | None = None):
    files = {"foto": ("objeto.png", foto or _png(), "image/png")}
    data = {
        "nombre": f"{PREFIX}Celular",
        "descripcion": "funda roja",
        "ambiente_id": str(lab["id"]),
        "encontrado_en": "2026-10-01T10:30:00-04:00",
    }
    return client.post(
        f"{API}/objetos-perdidos", data=data, files=files, headers=_auth(usuario)
    )


def test_lost_objects_crud_and_photos(lab, fotos_dir: Path) -> None:
    aux, enc, inv = lab["aux"], lab["enc"], lab["inv"]

    assert _registrar(lab, inv).status_code == 403
    r = _registrar(lab, aux)
    assert r.status_code == 201, r.text
    obj = r.json()
    assert obj["estado"] == "en_custodia"
    assert obj["encontro"]["nombre_completo"]
    assert obj["ambiente"]["codigo"].startswith(PREFIX)
    assert obj["foto_path"].startswith("objetos/") and obj["foto_path"].endswith(
        ".webp"
    )
    assert (fotos_dir / obj["foto_path"]).is_file()

    # Not an image -> 422 and no row.
    bad = client.post(
        f"{API}/objetos-perdidos",
        data={"nombre": f"{PREFIX}X", "ambiente_id": str(lab["id"])},
        files={"foto": ("x.png", b"not an image", "image/png")},
        headers=_auth(aux),
    )
    assert bad.status_code == 422

    foto_url = f"{API}/objetos-perdidos/{obj['id']}/fotos/objeto"
    assert client.get(foto_url).status_code == 401
    assert client.get(foto_url, headers=_auth(inv)).status_code == 403
    r = client.get(foto_url, headers=_auth(aux))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert (
        client.get(
            f"{API}/objetos-perdidos/{obj['id']}/fotos/entrega", headers=_auth(aux)
        ).status_code
        == 404
    )

    # Delivery (multipart with the delivery photo).
    entrega_url = f"{API}/objetos-perdidos/{obj['id']}/entrega"
    datos = {"entregado_a": "Juan Perez", "entregado_documento": "123"}
    archivos = {"foto": ("e.png", _png(), "image/png")}
    assert (
        client.post(
            entrega_url, data=datos, files=archivos, headers=_auth(inv)
        ).status_code
        == 403
    )
    r = client.post(entrega_url, data=datos, files=archivos, headers=_auth(aux))
    assert r.status_code == 200, r.text
    entregado = r.json()
    assert entregado["estado"] == "entregado"
    assert entregado["entrego"]["nombre_completo"]
    assert (fotos_dir / entregado["foto_entrega_path"]).is_file()
    # Already delivered: only managers may change it (trigger) and no file is left.
    antes = set(fotos_dir.rglob("*.webp"))
    r = client.post(entrega_url, data=datos, files=archivos, headers=_auth(aux))
    assert r.status_code == 422
    assert set(fotos_dir.rglob("*.webp")) == antes

    lista = client.get(f"{API}/objetos-perdidos", headers=_auth(aux)).json()
    assert obj["id"] in [o["id"] for o in lista]

    url = f"{API}/objetos-perdidos/{obj['id']}"
    assert client.delete(url, headers=_auth(aux)).status_code == 403
    assert client.delete(url, headers=_auth(enc)).status_code == 204
    assert not (fotos_dir / obj["foto_path"]).exists()
    assert not (fotos_dir / entregado["foto_entrega_path"]).exists()


def test_lost_object_photos_expire_after_nine_months(lab, fotos_dir: Path) -> None:
    aux, inv = lab["aux"], lab["inv"]
    obj = _registrar(lab, aux).json()
    ruta = fotos_dir / obj["foto_path"]
    with SessionLocal() as db:
        db.execute(
            text(
                "update horarios.objetos_perdidos"
                " set creado_en = now() - interval '10 months' where id = :id"
            ),
            {"id": obj["id"]},
        )
        db.commit()

    limpiar = f"{API}/objetos-perdidos/fotos/limpiar"
    assert client.post(limpiar).status_code == 401
    assert client.post(limpiar, headers=_auth(inv)).status_code == 403
    r = client.post(limpiar, headers=_auth(aux))
    assert r.status_code == 200, r.text
    assert r.json()["eliminadas"] >= 1
    assert not ruta.exists()
    lista = client.get(f"{API}/objetos-perdidos", headers=_auth(aux)).json()
    fila = next(o for o in lista if o["id"] == obj["id"])
    assert fila["foto_path"] is None and fila["fotos_borradas_en"]
