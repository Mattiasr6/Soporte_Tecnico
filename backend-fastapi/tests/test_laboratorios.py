"""Foundation tests for laboratorios service (Fase 1): models + migration only."""

import inspect
import os
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

from app.db.base import SessionLocal, engine
from app.main import app
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.usuario import Usuario

MIG_PATH = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0011_laboratorios.py"
)


def _mig():
    spec = spec_from_file_location("mig_0011_laboratorios", MIG_PATH)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MARK = "TEST-LAB-"


def _uid() -> int:
    with SessionLocal() as db:
        uid = db.scalar(select(func.min(Usuario.id)))
        assert uid is not None, "soporte_test has no Usuarios seed rows"
        return uid


def _limpiar() -> None:
    with SessionLocal() as db:
        db.execute(delete(LabAtencion).where(LabAtencion.auxiliar_nombre.like(f"{MARK}%")))
        db.execute(delete(Laboratorio).where(Laboratorio.codigo.like(f"{MARK}%")))
        db.execute(delete(LabCategoria).where(LabCategoria.nombre.like(f"{MARK}%")))
        db.commit()


@pytest.fixture(autouse=True)
def sin_residuos():
    _limpiar()
    yield
    _limpiar()


def _lab(codigo: str) -> Laboratorio:
    return Laboratorio(
        codigo=codigo, nombre=f"{codigo} nombre", activa=True, created_at=datetime.now(UTC)
    )


def test_duplicate_lab_codigo_fails():
    with SessionLocal() as db:
        db.add(_lab(f"{MARK}01"))
        db.commit()
        db.add(_lab(f"{MARK}01"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_unknown_category_rejected():
    with SessionLocal() as db:
        lab = _lab(f"{MARK}02")
        db.add(lab)
        db.commit()
        db.refresh(lab)
        db.add(
            LabAtencion(
                usuario_id=_uid(),
                laboratorio_id=lab.id,
                categoria_id=99999999,
                auxiliar_nombre=f"{MARK}aux",
                descripcion="d",
                solucion="s",
                fuera_de_turno=False,
                fecha_registro=datetime.now(UTC).date(),
                created_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_downgrade_reverts_without_touching_soporte_tables():
    src = inspect.getsource(_mig().downgrade)
    assert src.index('drop_table("LabAtenciones")') < src.index(
        'drop_table("LabCategorias")'
    ) < src.index('drop_table("Laboratorios")')
    for tabla in (
        '"Atenciones"',
        '"Usuarios"',
        '"Sugerencias"',
        '"Areas"',
        '"Grupos"',
        '"Horarios"',
    ):
        assert tabla not in src, tabla
    inspector = sa_inspect(engine)
    tablas = set(inspector.get_table_names())
    assert {"Laboratorios", "LabCategorias", "LabAtenciones"} <= tablas


client = TestClient(app)

UID_TEC = 2
UID_JEFE = 8
EMAILS = {
    2: "diego.orihuela@upds.edu.bo",
    8: "josue.huayllas@upds.edu.bo",
}
_tokens: dict[int, str] = {}


def h(uid: int) -> dict[str, str]:
    if uid not in _tokens:
        r = client.post(
            "/api/auth/login",
            json={"email": EMAILS[uid], "password": os.environ["SEED_PASSWORD"]},
        )
        assert r.status_code == 200, r.text
        _tokens[uid] = r.json()["token"]
    return {"Authorization": f"Bearer {_tokens[uid]}"}


AMARK = "TEST-LAB-API-"
CMARK = "TEST-LAB-CAT-"


def _limpiar_api() -> None:
    with SessionLocal() as db:
        db.execute(
            delete(LabAtencion).where(LabAtencion.descripcion.like(f"{AMARK}%"))
        )
        db.execute(delete(Laboratorio).where(Laboratorio.codigo.like(f"{AMARK}%")))
        db.execute(delete(LabCategoria).where(LabCategoria.nombre.like(f"{CMARK}%")))
        db.commit()


@pytest.fixture
def api_limpia():
    _limpiar_api()
    yield
    _limpiar_api()


def _crear_lab(codigo: str, nombre: str | None = None) -> dict[str, Any]:
    r = client.post(
        "/api/laboratorios/",
        json={"codigo": codigo, "nombre": nombre or f"{codigo} nombre"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_cat(nombre: str) -> dict[str, Any]:
    r = client.post(
        "/api/laboratorios/categorias",
        json={"nombre": nombre},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_atencion(
    lab_id: int, categoria: str, descripcion: str, uid: int
) -> dict[str, Any]:
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab_id,
            "categoria": categoria,
            "descripcion": descripcion,
            "solucion": "reinicio",
        },
        headers=h(uid),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_cards_incluye_seeds(api_limpia):
    r = client.get("/api/laboratorios/cards", headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"activas", "inactivas"}
    assert {c["codigo"] for c in body["activas"]} >= {f"LAB-{i:02d}" for i in range(1, 11)}
    assert client.get("/api/laboratorios/cards").status_code == 401


def test_lab_crud_jefe_y_403_tecnico(api_limpia):
    lab = _crear_lab(f"{AMARK}01")
    assert lab["activa"] is True
    dup = client.post(
        "/api/laboratorios/",
        json={"codigo": f"{AMARK}01", "nombre": "otro"},
        headers=h(UID_JEFE),
    )
    assert dup.status_code == 400
    r = client.post(
        "/api/laboratorios/",
        json={"codigo": f"{AMARK}99", "nombre": "x"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 403
    assert (
        client.put(
            f"/api/laboratorios/{lab['id']}",
            json={"activa": False},
            headers=h(UID_TEC),
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/laboratorios/{lab['id']}",
            json={"activa": False},
            headers=h(UID_JEFE),
        ).status_code
        == 204
    )
    body = client.get("/api/laboratorios/cards", headers=h(UID_JEFE)).json()
    assert lab["id"] in [c["id"] for c in body["inactivas"]]


def test_categorias_todas_requiere_jefe(api_limpia):
    cat = _crear_cat(f"{CMARK}Redes")
    dup = client.post(
        "/api/laboratorios/categorias",
        json={"nombre": f"  {CMARK.lower()}redes  "},
        headers=h(UID_JEFE),
    )
    assert dup.status_code == 400
    assert (
        client.get(
            "/api/laboratorios/categorias", params={"todas": True}, headers=h(UID_TEC)
        ).status_code
        == 403
    )
    publicas = client.get(
        "/api/laboratorios/categorias", headers=h(UID_TEC)
    ).json()
    assert cat["id"] in [c["id"] for c in publicas]
    assert (
        client.put(
            f"/api/laboratorios/categorias/{cat['id']}",
            json={"activa": False},
            headers=h(UID_JEFE),
        ).status_code
        == 204
    )
    publicas = client.get(
        "/api/laboratorios/categorias", headers=h(UID_TEC)
    ).json()
    assert cat["id"] not in [c["id"] for c in publicas]


def test_post_atencion_422_inactiva_o_desconocida(api_limpia):
    lab = _crear_lab(f"{AMARK}02")
    cat = _crear_cat(f"{CMARK}Soporte")
    payload = {
        "laboratorio_id": lab["id"],
        "categoria": cat["nombre"],
        "descripcion": f"{AMARK}desc",
        "solucion": "s",
    }
    client.put(
        f"/api/laboratorios/{lab['id']}", json={"activa": False}, headers=h(UID_JEFE)
    )
    r = client.post(
        "/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC)
    )
    assert r.status_code == 422
    client.put(
        f"/api/laboratorios/{lab['id']}", json={"activa": True}, headers=h(UID_JEFE)
    )
    client.put(
        f"/api/laboratorios/categorias/{cat['id']}",
        json={"activa": False},
        headers=h(UID_JEFE),
    )
    r = client.post(
        "/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC)
    )
    assert r.status_code == 422
    payload["categoria"] = "NoExiste jamas"
    r = client.post(
        "/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC)
    )
    assert r.status_code == 422


def test_post_atencion_409_duplicada_60s(api_limpia):
    lab = _crear_lab(f"{AMARK}03")
    cat = _crear_cat(f"{CMARK}Dup")
    desc = f"{AMARK}dup-unica"
    primera = _crear_atencion(lab["id"], cat["nombre"], desc, UID_TEC)
    assert isinstance(primera["fuera_de_turno"], bool)
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": desc,
            "solucion": "otra",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 409


def test_get_atenciones_ambito_y_orden(api_limpia):
    lab = _crear_lab(f"{AMARK}04")
    cat = _crear_cat(f"{CMARK}Ambito")
    a1 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}una", UID_TEC)
    a2 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}otra", UID_JEFE)
    propias = client.get(
        "/api/laboratorios/atenciones", headers=h(UID_TEC)
    ).json()
    assert all(a["usuario_id"] == UID_TEC for a in propias)
    assert a1["id"] in [a["id"] for a in propias]
    assert a2["id"] not in [a["id"] for a in propias]
    todas = client.get(
        "/api/laboratorios/atenciones", headers=h(UID_JEFE)
    ).json()
    ids = [a["id"] for a in todas if a["descripcion"].startswith(AMARK)]
    assert a1["id"] in ids and a2["id"] in ids
    assert ids == sorted(ids, reverse=True)
    filtradas = client.get(
        "/api/laboratorios/atenciones",
        params={"usuario_id": UID_TEC},
        headers=h(UID_JEFE),
    ).json()
    assert all(a["usuario_id"] == UID_TEC for a in filtradas)


def test_put_delete_owner_o_jefe(api_limpia):
    lab = _crear_lab(f"{AMARK}05")
    cat = _crear_cat(f"{CMARK}Permisos")
    creada = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}perm", UID_TEC)
    tid = creada["id"]
    assert (
        client.put(
            f"/api/laboratorios/atenciones/{tid}",
            json={"solucion": "cambio jefe"},
            headers=h(UID_JEFE),
        ).status_code
        == 204
    )
    assert (
        client.put(
            f"/api/laboratorios/atenciones/{tid}",
            json={"solucion": "cambio dueño"},
            headers=h(UID_TEC),
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/laboratorios/atenciones/{tid}", headers=h(UID_JEFE)
        ).status_code
        == 204
    )
    todas = client.get(
        "/api/laboratorios/atenciones", headers=h(UID_JEFE)
    ).json()
    assert tid not in [a["id"] for a in todas]


def test_stats_privilegiado_y_filtros(api_limpia):
    assert (
        client.get("/api/laboratorios/stats", headers=h(UID_TEC)).status_code == 401
    )
    assert client.get("/api/laboratorios/stats").status_code == 401
    lab = _crear_lab(f"{AMARK}06")
    cat = _crear_cat(f"{CMARK}Stats")
    _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}s1", UID_TEC)
    s = client.get("/api/laboratorios/stats", headers=h(UID_JEFE)).json()
    assert set(s) == {"total", "por_lab", "por_categoria", "por_mes"}
    assert s["total"] >= 1
    assert sum(p["total"] for p in s["por_lab"]) == s["total"]
    assert sum(p["total"] for p in s["por_categoria"]) == s["total"]
    assert sum(p["total"] for p in s["por_mes"]) == s["total"]
    assert all(set(p) == {"categoria", "total"} for p in s["por_categoria"])
    assert all(set(p) == {"anio", "mes", "total"} for p in s["por_mes"])
    vacio = _crear_lab(f"{AMARK}07")
    s0 = client.get(
        "/api/laboratorios/stats",
        params={"laboratorio_id": vacio["id"]},
        headers=h(UID_JEFE),
    ).json()
    assert s0["total"] == 0
    assert any(p["total"] == 0 for p in s0["por_lab"])
    mes = datetime.now(UTC).strftime("%Y-%m")
    s1 = client.get(
        "/api/laboratorios/stats",
        params={"laboratorio_id": lab["id"], "desde_ym": mes, "hasta_ym": mes},
        headers=h(UID_JEFE),
    ).json()
    assert s1["total"] >= 1
    assert (
        client.get(
            "/api/laboratorios/stats",
            params={"desde_ym": "no-es-mes"},
            headers=h(UID_JEFE),
        ).status_code
        == 400
    )


def test_export_csv(api_limpia):
    assert (
        client.get("/api/laboratorios/export.csv", headers=h(UID_TEC)).status_code
        == 401
    )
    lab = _crear_lab(f"{AMARK}08")
    cat = _crear_cat(f"{CMARK}Csv")
    _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}csv1", UID_TEC)
    r = client.get("/api/laboratorios/export.csv", headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    lineas = r.text.strip().splitlines()
    assert lineas[0] == (
        "id,laboratorio,categoria,auxiliar,descripcion,fecha_registro,fuera_de_turno"
    )
    assert any(f"{AMARK}csv1" in linea for linea in lineas[1:])
    r2 = client.get(
        "/api/laboratorios/export.csv",
        params={"laboratorio_id": lab["id"]},
        headers=h(UID_JEFE),
    )
    assert r2.status_code == 200
    assert any(f"{AMARK}csv1" in linea for linea in r2.text.strip().splitlines()[1:])


def test_stats_shape_parity_con_atenciones(api_limpia):
    """LabStatsOut comparte total/por_categoria/por_mes con StatsOut (Fase 4)."""
    from app.schemas.atencion import PorCategoria as AtPorCategoria
    from app.schemas.atencion import PorMes as AtPorMes
    from app.schemas.atencion import StatsOut
    from app.schemas.laboratorio import LabStatsOut
    from app.schemas.laboratorio import PorCategoria as LabPorCategoria
    from app.schemas.laboratorio import PorMes as LabPorMes

    assert LabPorCategoria is AtPorCategoria
    assert LabPorMes is AtPorMes
    assert {"total", "por_categoria", "por_mes"} <= set(StatsOut.model_fields)
    assert {"total", "por_categoria", "por_mes"} <= set(LabStatsOut.model_fields)
    lab = _crear_lab(f"{AMARK}09")
    cat = _crear_cat(f"{CMARK}Parity")
    _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}parity1", UID_TEC)
    s_lab = client.get("/api/laboratorios/stats", headers=h(UID_JEFE)).json()
    for clave in ("total", "por_categoria", "por_mes"):
        assert clave in s_lab
    assert set(s_lab["por_categoria"][0]) == {"categoria", "total"}
    assert set(s_lab["por_mes"][0]) == {"anio", "mes", "total"}


def test_export_csv_vacio_y_filtros_estrictos(api_limpia):
    lab_a = _crear_lab(f"{AMARK}10")
    lab_b = _crear_lab(f"{AMARK}11")
    cat = _crear_cat(f"{CMARK}Csv2")
    _crear_atencion(lab_a["id"], cat["nombre"], f"{AMARK}csvA", UID_TEC)
    _crear_atencion(lab_b["id"], cat["nombre"], f"{AMARK}csvB", UID_TEC)
    vacio = _crear_lab(f"{AMARK}12")
    r0 = client.get(
        "/api/laboratorios/export.csv",
        params={"laboratorio_id": vacio["id"]},
        headers=h(UID_JEFE),
    )
    assert r0.status_code == 200, r0.text
    lineas0 = r0.text.strip().splitlines()
    assert lineas0 == [
        "id,laboratorio,categoria,auxiliar,descripcion,fecha_registro,fuera_de_turno"
    ]
    r1 = client.get(
        "/api/laboratorios/export.csv",
        params={"laboratorio_id": lab_a["id"]},
        headers=h(UID_JEFE),
    )
    assert r1.status_code == 200, r1.text
    lineas1 = r1.text.strip().splitlines()
    assert lineas1[0] == (
        "id,laboratorio,categoria,auxiliar,descripcion,fecha_registro,fuera_de_turno"
    )
    assert any(f"{AMARK}csvA" in linea for linea in lineas1[1:])
    assert not any(f"{AMARK}csvB" in linea for linea in lineas1)


def test_submit_guard_descripciones_distintas_ok(api_limpia):
    lab = _crear_lab(f"{AMARK}13")
    cat = _crear_cat(f"{CMARK}Guard")
    a1 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}guard-uno", UID_TEC)
    a2 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}guard-dos", UID_TEC)
    assert a1["id"] != a2["id"]
