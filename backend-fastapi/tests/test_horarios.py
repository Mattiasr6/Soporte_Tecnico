"""Tests del horario por dia, la cobertura separada y el turno fijo de los jefes.

Usa mes 1 / anio 2099 para no tocar datos reales y limpia al final.
"""

import os
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.horario import Horario

UID_DIEGO = 2
UID_PAUL = 3
UID_JEFE = 8

MES, ANIO = 1, 2099
LUNES, SABADO = 1, 6

client = TestClient(app)
EMAILS = {
    2: "diego.orihuela@upds.edu.bo",
    3: "paul.quispe@upds.edu.bo",
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


def _horario(usuario_id: int, dia: int, inicio1: str, fin1: str) -> dict[str, object]:
    return {
        "usuario_id": usuario_id,
        "dia_semana": dia,
        "hora_inicio1": inicio1,
        "hora_fin1": fin1,
        "hora_inicio2": None,
        "hora_fin2": None,
        "mes": MES,
        "anio": ANIO,
    }


def _limpiar() -> None:
    with SessionLocal() as db:
        for fila in db.scalars(
            select(Horario).where(Horario.mes == MES, Horario.anio == ANIO)
        ).all():
            db.delete(fila)
        db.commit()


def _cobertura() -> dict[str, Any]:
    r = client.get(
        "/api/horarios/cobertura",
        params={"mes": MES, "anio": ANIO},
        headers=h(UID_JEFE),
    )
    assert r.status_code == 200, r.text
    return r.json()


def _franja(bloques: list[dict[str, Any]], nombre: str) -> list[str]:
    return next(f["tecnicos"] for f in bloques if f["franja"] == nombre)


def test_lote_guarda_los_cinco_dias_de_una():
    _limpiar()
    try:
        lote = {
            "asignaciones": [
                _horario(UID_DIEGO, dia, "08:00", "16:00") for dia in range(1, 6)
            ]
        }
        assert (
            client.post(
                "/api/horarios/lote", json=lote, headers=h(UID_JEFE)
            ).status_code
            == 204
        )
        rows = client.get(
            "/api/horarios", params={"mes": MES, "anio": ANIO}, headers=h(UID_JEFE)
        ).json()
        assert len(rows) == 5
        assert sorted(r["dia_semana"] for r in rows) == [1, 2, 3, 4, 5]

        vacio = client.post(
            "/api/horarios/lote", json={"asignaciones": []}, headers=h(UID_JEFE)
        )
        assert vacio.status_code == 400
    finally:
        _limpiar()


def test_cobertura_separa_laborable_de_sabado_y_excluye_jefes():
    _limpiar()
    try:
        for dto in (
            _horario(UID_DIEGO, LUNES, "08:00", "16:00"),
            _horario(UID_DIEGO, SABADO, "08:00", "12:00"),
            _horario(UID_PAUL, LUNES, "12:00", "20:00"),
            _horario(UID_PAUL, SABADO, "14:30", "18:30"),
            _horario(UID_JEFE, LUNES, "08:00", "12:00"),
        ):
            assert (
                client.post("/api/horarios", json=dto, headers=h(UID_JEFE)).status_code
                == 204
            )

        datos = _cobertura()
        assert datos["mes"] == MES and datos["anio"] == ANIO
        assert len(datos["laborable"]) == 4 and len(datos["sabado"]) == 4

        laborable = datos["laborable"]
        assert _franja(laborable, "Mañana") == ["Diego Orihuela Herrera"]
        assert sorted(_franja(laborable, "Medio día")) == sorted(
            ["Diego Orihuela Herrera", "Paul Manuel Quispe Choque"]
        )
        assert _franja(laborable, "Noche") == ["Paul Manuel Quispe Choque"]

        sabado = datos["sabado"]
        assert _franja(sabado, "Mañana") == ["Diego Orihuela Herrera"]
        assert _franja(sabado, "Medio día") == []
        assert _franja(sabado, "Tarde") == ["Paul Manuel Quispe Choque"]
        assert _franja(sabado, "Noche") == []

        todos = [
            n for bloque in (laborable, sabado) for f in bloque for n in f["tecnicos"]
        ]
        assert "Josue Huayllas" not in todos
    finally:
        _limpiar()


def test_eliminar_el_horario_de_un_dia():
    _limpiar()
    try:
        dto = _horario(UID_DIEGO, LUNES, "08:00", "16:00")
        assert (
            client.post("/api/horarios", json=dto, headers=h(UID_JEFE)).status_code
            == 204
        )
        r = client.delete(
            "/api/horarios",
            params={
                "usuario_id": UID_DIEGO,
                "mes": MES,
                "anio": ANIO,
                "dia_semana": LUNES,
            },
            headers=h(UID_JEFE),
        )
        assert r.status_code == 204
        rows = client.get(
            "/api/horarios", params={"mes": MES, "anio": ANIO}, headers=h(UID_JEFE)
        ).json()
        assert rows == []
    finally:
        _limpiar()


def test_sin_horario_hoy_figura_fuera_de_turno():
    """El usuario ya cargo horarios reales, asi que el test limpia el turno de hoy de
    una persona y lo restaura: no depende de que el mes este vacio."""
    from datetime import UTC, datetime

    from app.models.usuario import Usuario
    from app.routers.usuarios import _hoy_local

    mes, anio, dia = _hoy_local()
    respaldo: list[dict[str, Any]] = []
    with SessionLocal() as db:
        for fila in db.scalars(
            select(Horario).where(
                Horario.usuario_id == UID_DIEGO,
                Horario.mes == mes,
                Horario.anio == anio,
                Horario.dia_semana == dia,
            )
        ).all():
            respaldo.append(
                {
                    "label": fila.label,
                    "hora_inicio1": fila.hora_inicio1,
                    "hora_fin1": fila.hora_fin1,
                    "hora_inicio2": fila.hora_inicio2,
                    "hora_fin2": fila.hora_fin2,
                }
            )
            db.delete(fila)
        usuario = db.get(Usuario, UID_DIEGO)
        assert usuario is not None
        estado_previo = usuario.estado_actual
        db.commit()

    try:
        assert (
            client.patch(
                "/api/usuarios/estado",
                json={"estado_actual": "disponible"},
                headers=h(UID_DIEGO),
            ).status_code
            == 204
        )
        usuarios = client.get("/api/usuarios", headers=h(UID_JEFE)).json()
        diego = next(u for u in usuarios if u["id"] == UID_DIEGO)
        assert diego["estado_actual"] == "extraturno"
    finally:
        with SessionLocal() as db:
            for datos in respaldo:
                db.add(
                    Horario(
                        usuario_id=UID_DIEGO,
                        mes=mes,
                        anio=anio,
                        dia_semana=dia,
                        created_at=datetime.now(UTC),
                        **datos,
                    )
                )
            usuario = db.get(Usuario, UID_DIEGO)
            assert usuario is not None
            usuario.estado_actual = estado_previo
            db.commit()
