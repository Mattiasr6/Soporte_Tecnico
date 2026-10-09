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
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "0011_laboratorios.py"
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
        db.execute(
            delete(LabAtencion).where(LabAtencion.auxiliar_nombre.like(f"{MARK}%"))
        )
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
        codigo=codigo,
        nombre=f"{codigo} nombre",
        activa=True,
        created_at=datetime.now(UTC),
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
    assert (
        src.index('drop_table("LabAtenciones")')
        < src.index('drop_table("LabCategorias")')
        < src.index('drop_table("Laboratorios")')
    )
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
        db.execute(delete(LabAtencion).where(LabAtencion.descripcion.like(f"{AMARK}%")))
        db.execute(delete(Laboratorio).where(Laboratorio.codigo.like(f"{AMARK}%")))
        db.execute(delete(LabCategoria).where(LabCategoria.nombre.like(f"{CMARK}%")))
        db.commit()


@pytest.fixture
def api_limpia():
    _limpiar_api()
    yield
    _limpiar_api()


CSV_HEADER_LAB = "id,laboratorio,categoria,auxiliar,turno,medio,descripcion,fecha_registro,fuera_de_turno"


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
    client.post(
        "/api/laboratorios/equipo",
        json={"nombre": f"{MARK}aux"},
        headers=h(UID_JEFE),
    )
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab_id,
            "categoria": categoria,
            "descripcion": descripcion,
            "solucion": "reinicio",
            "auxiliar_nombre": f"{MARK}aux",
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
    assert {c["codigo"] for c in body["activas"]} >= {
        f"LAB-{i:02d}" for i in range(1, 11)
    }
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
    publicas = client.get("/api/laboratorios/categorias", headers=h(UID_TEC)).json()
    assert cat["id"] in [c["id"] for c in publicas]
    assert (
        client.put(
            f"/api/laboratorios/categorias/{cat['id']}",
            json={"activa": False},
            headers=h(UID_JEFE),
        ).status_code
        == 204
    )
    publicas = client.get("/api/laboratorios/categorias", headers=h(UID_TEC)).json()
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
    r = client.post("/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC))
    assert r.status_code == 422
    client.put(
        f"/api/laboratorios/{lab['id']}", json={"activa": True}, headers=h(UID_JEFE)
    )
    client.put(
        f"/api/laboratorios/categorias/{cat['id']}",
        json={"activa": False},
        headers=h(UID_JEFE),
    )
    r = client.post("/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC))
    assert r.status_code == 422
    payload["categoria"] = "NoExiste jamas"
    r = client.post("/api/laboratorios/atenciones", json=payload, headers=h(UID_TEC))
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
            "auxiliar_nombre": f"{MARK}aux",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 409


def test_get_atenciones_ambito_y_orden(api_limpia):
    lab = _crear_lab(f"{AMARK}04")
    cat = _crear_cat(f"{CMARK}Ambito")
    a1 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}una", UID_TEC)
    a2 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}otra", UID_JEFE)
    propias = client.get("/api/laboratorios/atenciones", headers=h(UID_TEC)).json()
    assert all(a["usuario_id"] == UID_TEC for a in propias)
    assert a1["id"] in [a["id"] for a in propias]
    assert a2["id"] not in [a["id"] for a in propias]
    todas = client.get("/api/laboratorios/atenciones", headers=h(UID_JEFE)).json()
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
    todas = client.get("/api/laboratorios/atenciones", headers=h(UID_JEFE)).json()
    assert tid not in [a["id"] for a in todas]


def test_stats_privilegiado_y_filtros(api_limpia):
    assert client.get("/api/laboratorios/stats", headers=h(UID_TEC)).status_code == 401
    assert client.get("/api/laboratorios/stats").status_code == 401
    lab = _crear_lab(f"{AMARK}06")
    cat = _crear_cat(f"{CMARK}Stats")
    _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}s1", UID_TEC)
    s = client.get("/api/laboratorios/stats", headers=h(UID_JEFE)).json()
    assert {"total", "por_lab", "por_categoria", "por_mes", "por_turno", "fuera_por_turno", "fuera_por_auxiliar"} <= set(s)
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
    assert lineas[0] == CSV_HEADER_LAB
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
    assert lineas0 == [CSV_HEADER_LAB]
    r1 = client.get(
        "/api/laboratorios/export.csv",
        params={"laboratorio_id": lab_a["id"]},
        headers=h(UID_JEFE),
    )
    assert r1.status_code == 200, r1.text
    lineas1 = r1.text.strip().splitlines()
    assert lineas1[0] == CSV_HEADER_LAB
    assert any(f"{AMARK}csvA" in linea for linea in lineas1[1:])
    assert not any(f"{AMARK}csvB" in linea for linea in lineas1)


def test_submit_guard_descripciones_distintas_ok(api_limpia):
    lab = _crear_lab(f"{AMARK}13")
    cat = _crear_cat(f"{CMARK}Guard")
    a1 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}guard-uno", UID_TEC)
    a2 = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}guard-dos", UID_TEC)
    assert a1["id"] != a2["id"]


REALES = (
    "HARDWARE",
    "RED E INTERNET",
    "INFRAESTRUCTURA",
    "SOFTWARE",
    "SOPORTE ACADÉMICO",
    "SEGURIDAD",
    "INVENTARIO",
    "SOPORTE EN LABORATORIOS",
    "REPORTE Y GESTIÓN",
)
GENERICS = (
    "Mantenimiento preventivo",
    "Mantenimiento correctivo",
    "Calibración",
    "Otros",
)


def test_seeds_reales_con_guia_y_sin_genericas(api_limpia):
    r = client.get("/api/laboratorios/categorias", headers=h(UID_TEC))
    assert r.status_code == 200, r.text
    por_nombre = {c["nombre"]: c for c in r.json()}
    for nombre in REALES:
        assert nombre in por_nombre, nombre
        guia = por_nombre[nombre].get("descripcion") or ""
        assert len(guia) > 20, nombre
        assert "," in guia, nombre
    for nombre in GENERICS:
        assert nombre not in por_nombre, nombre


def test_guia_visible_en_payload_todas(api_limpia):
    r = client.get(
        "/api/laboratorios/categorias",
        params={"todas": True},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    por_nombre = {c["nombre"]: c for c in r.json()}
    assert set(REALES) <= set(por_nombre)
    assert "Equipo no enciende" in (por_nombre["HARDWARE"].get("descripcion") or "")
    assert "FortiGate" in (por_nombre["RED E INTERNET"].get("descripcion") or "")
    assert "robótica" in (
        por_nombre["SOPORTE EN LABORATORIOS"].get("descripcion") or ""
    )


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EQUIPO_FILE = DATA_DIR / "equipo_auxiliares.json"
HORARIOS_FILE = DATA_DIR / "horarios_auxiliares.json"


@pytest.fixture
def archivos_data():
    respaldo = {
        p: p.read_bytes() if p.exists() else None for p in (EQUIPO_FILE, HORARIOS_FILE)
    }
    client.put("/api/laboratorios/equipo", json={"auxiliares": []}, headers=h(UID_JEFE))
    yield
    for ruta, contenido in respaldo.items():
        if contenido is None:
            if ruta.exists():
                ruta.unlink()
        else:
            ruta.write_bytes(contenido)


AUX = "TEST-LAB-AUX-"


def _agregar_aux(nombre: str) -> None:
    r = client.post(
        "/api/laboratorios/equipo", json={"nombre": nombre}, headers=h(UID_JEFE)
    )
    assert r.status_code in (200, 400), r.text


def test_equipo_crud_jefe_y_403_tecnico(api_limpia, archivos_data):
    r = client.post(
        "/api/laboratorios/equipo",
        json={"nombre": f"{AUX}1"},
        headers=h(UID_TEC),
    )
    assert r.status_code == 403
    assert (
        client.put(
            "/api/laboratorios/equipo",
            json={"auxiliares": []},
            headers=h(UID_TEC),
        ).status_code
        == 403
    )
    r = client.post(
        "/api/laboratorios/equipo",
        json={"nombre": f"{AUX}1"},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {
        "nombre": f"{AUX}1",
        "activo": True,
        "encargado": False,
        "usuario_id": None,
    }
    dup = client.post(
        "/api/laboratorios/equipo",
        json={"nombre": f"  {AUX.lower()}1  "},
        headers=h(UID_JEFE),
    )
    assert dup.status_code == 400
    vacio = client.post(
        "/api/laboratorios/equipo", json={"nombre": "   "}, headers=h(UID_JEFE)
    )
    assert vacio.status_code == 400
    r = client.put(
        "/api/laboratorios/equipo",
        json={"auxiliares": [{"nombre": f"{AUX}2", "activo": True}]},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    assert [m["nombre"] for m in r.json()["auxiliares"]] == [f"{AUX}2"]
    assert (
        client.put(
            "/api/laboratorios/equipo",
            json={"auxiliares": [{"nombre": f"{AUX}2"}, {"nombre": f"{AUX}2"}]},
            headers=h(UID_JEFE),
        ).status_code
        == 400
    )
    body = client.get("/api/laboratorios/equipo", headers=h(UID_TEC)).json()
    assert [m["nombre"] for m in body["auxiliares"]] == [f"{AUX}2"]


def test_horarios_put_y_conteo(api_limpia, archivos_data):
    _agregar_aux(f"{AUX}1")
    _agregar_aux(f"{AUX}2")
    base = {
        "mañana": {"inicio": "07:00", "fin": "12:00", "auxiliares": [f"{AUX}1"]},
        "mediodia": {"inicio": "12:00", "fin": "16:00", "auxiliares": []},
        "tarde": {"inicio": "14:30", "fin": "18:30", "auxiliares": [f"{AUX}2"]},
        "noche": {"inicio": "18:00", "fin": "22:00", "auxiliares": []},
    }
    assert (
        client.put(
            "/api/laboratorios/horarios", json=base, headers=h(UID_TEC)
        ).status_code
        == 403
    )
    incompleto = dict(base)
    del incompleto["noche"]
    assert (
        client.put(
            "/api/laboratorios/horarios", json=incompleto, headers=h(UID_JEFE)
        ).status_code
        == 400
    )
    mala_hora = {t: dict(b) for t, b in base.items()}
    mala_hora["mañana"] = {"inicio": "7am", "fin": "12:00", "auxiliares": []}
    assert (
        client.put(
            "/api/laboratorios/horarios", json=mala_hora, headers=h(UID_JEFE)
        ).status_code
        == 400
    )
    fantasma = {t: dict(b) for t, b in base.items()}
    fantasma["tarde"] = {
        "inicio": "14:30",
        "fin": "18:30",
        "auxiliares": ["No Existe Jamas"],
    }
    assert (
        client.put(
            "/api/laboratorios/horarios", json=fantasma, headers=h(UID_JEFE)
        ).status_code
        == 400
    )
    r = client.put("/api/laboratorios/horarios", json=base, headers=h(UID_JEFE))
    assert r.status_code == 200, r.text
    assert r.json()["tarde"]["auxiliares"] == [f"{AUX}2"]
    conteo = client.get("/api/laboratorios/horarios/conteo", headers=h(UID_TEC)).json()
    assert conteo == {"mañana": 1, "mediodia": 0, "tarde": 1, "noche": 0}


def test_atencion_con_turno_guarda_turno(api_limpia, archivos_data):
    _agregar_aux(f"{AUX}1")
    _agregar_aux(f"{AUX}2")
    client.put(
        "/api/laboratorios/horarios",
        json={
            "mañana": {"inicio": "07:00", "fin": "12:00", "auxiliares": [f"{AUX}1"]},
            "mediodia": {"inicio": "12:00", "fin": "16:00", "auxiliares": []},
            "tarde": {"inicio": "14:30", "fin": "18:30", "auxiliares": [f"{AUX}2"]},
            "noche": {"inicio": "18:00", "fin": "22:00", "auxiliares": []},
        },
        headers=h(UID_JEFE),
    )
    lab = _crear_lab(f"{AMARK}14")
    cat = _crear_cat(f"{CMARK}Turno")
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": f"{AMARK}turno-1",
            "solucion": "s",
            "auxiliar_nombre": f"{AUX}2",
            "turno": "tarde",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 200, r.text
    assert r.json()["turno"] == "tarde"
    mala = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": f"{AMARK}turno-malo",
            "solucion": "s",
            "turno": "madrugada",
        },
        headers=h(UID_TEC),
    )
    assert mala.status_code == 400
    sug = client.get(
        "/api/laboratorios/equipo", params={"turno": "tarde"}, headers=h(UID_TEC)
    ).json()
    assert [m["nombre"] for m in sug["auxiliares"]] == [f"{AUX}2"]
    assert (
        client.get(
            "/api/laboratorios/equipo",
            params={"turno": "madrugada"},
            headers=h(UID_TEC),
        ).status_code
        == 400
    )
    stats = client.get("/api/laboratorios/stats", headers=h(UID_JEFE)).json()
    por_turno = {p["turno"]: p["total"] for p in stats["por_turno"]}
    assert por_turno.get("tarde", 0) >= 1
    filtrado = client.get(
        "/api/laboratorios/stats",
        params={"turno": "tarde"},
        headers=h(UID_JEFE),
    ).json()
    assert filtrado["total"] >= 1
    csv = client.get(
        "/api/laboratorios/export.csv",
        params={"turno": "tarde"},
        headers=h(UID_JEFE),
    )
    assert csv.status_code == 200, csv.text
    assert any("tarde" in linea for linea in csv.text.strip().splitlines()[1:])


def test_medio_default_presencial(api_limpia):
    lab = _crear_lab(f"{AMARK}15")
    cat = _crear_cat(f"{CMARK}Medio")
    a = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}medio-def", UID_TEC)
    assert a["medio_solicitud"] == "Presencial"


def test_medio_invalido_400(api_limpia):
    lab = _crear_lab(f"{AMARK}16")
    cat = _crear_cat(f"{CMARK}MedioMalo")
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": f"{AMARK}medio-malo",
            "solucion": "s",
            "auxiliar_nombre": f"{MARK}aux",
            "medio_solicitud": "Email",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 400
    creada = _crear_atencion(lab["id"], cat["nombre"], f"{AMARK}medio-ok", UID_TEC)
    r2 = client.put(
        f"/api/laboratorios/atenciones/{creada['id']}",
        json={"medio_solicitud": "Paloma"},
        headers=h(UID_TEC),
    )
    assert r2.status_code == 400


def test_medio_roundtrip_whatsapp(api_limpia):
    lab = _crear_lab(f"{AMARK}17")
    cat = _crear_cat(f"{CMARK}MedioWa")
    _agregar_aux(f"{MARK}aux")
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": f"{AMARK}medio-wa",
            "solucion": "s",
            "auxiliar_nombre": f"{MARK}aux",
            "medio_solicitud": "WhatsApp",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 200, r.text
    assert r.json()["medio_solicitud"] == "WhatsApp"
    tid = r.json()["id"]
    assert (
        client.put(
            f"/api/laboratorios/atenciones/{tid}",
            json={"medio_solicitud": "Presencial"},
            headers=h(UID_TEC),
        ).status_code
        == 204
    )
    got = client.get(f"/api/laboratorios/atenciones/{tid}", headers=h(UID_TEC)).json()
    assert got["medio_solicitud"] == "Presencial"
    csv = client.get(
        "/api/laboratorios/export.csv",
        params={"laboratorio_id": lab["id"]},
        headers=h(UID_JEFE),
    )
    assert csv.status_code == 200, csv.text
    lineas = csv.text.strip().splitlines()
    assert lineas[0] == CSV_HEADER_LAB
    assert any("Presencial" in linea for linea in lineas[1:])


def test_auxiliar_desconocido_400(api_limpia):
    lab = _crear_lab(f"{AMARK}18")
    cat = _crear_cat(f"{CMARK}AuxDesc")
    r = client.post(
        "/api/laboratorios/atenciones",
        json={
            "laboratorio_id": lab["id"],
            "categoria": cat["nombre"],
            "descripcion": f"{AMARK}aux-desc",
            "solucion": "s",
            "auxiliar_nombre": "Nadie Inexistente",
        },
        headers=h(UID_TEC),
    )
    assert r.status_code == 400, r.text


def test_forzar_duplicado_permite_clonar(api_limpia, archivos_data):
    _agregar_aux(f"{AUX}Dup")
    lab = _crear_lab(f"{AMARK}DUP")
    cat = _crear_cat(f"{CMARK}dup")
    dto = {
        "laboratorio_id": lab["id"],
        "categoria": cat["nombre"],
        "descripcion": f"{AMARK}misma desc",
        "solucion": "s",
        "auxiliar_nombre": f"{AUX}Dup",
    }
    assert (
        client.post(
            "/api/laboratorios/atenciones", json=dto, headers=h(UID_JEFE)
        ).status_code
        == 200
    )
    # sin flag: el guard de 60s bloquea
    assert (
        client.post(
            "/api/laboratorios/atenciones", json=dto, headers=h(UID_JEFE)
        ).status_code
        == 409
    )
    # con flag (clonador): permite
    r = client.post(
        "/api/laboratorios/atenciones",
        json={**dto, "forzar_duplicado": True},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
