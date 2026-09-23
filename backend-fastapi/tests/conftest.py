"""Fixtures compartidas.

El equipo ya tiene horarios reales cargados, así que un test que necesite estar
en turno se fabrica su propia ventana para hoy y la restaura al salir: si no,
el resultado dependería de la hora a la que se corra la suite.

La preparación va DENTRO del try: si falla a mitad, el finally igual restaura y
la base no queda con el turno de prueba pegado.

Ojo: la regla mira el reloj, así que si la suite corre justo al cruzar la
medianoche estos tests pueden fallar por el cambio de día (ventana de ~1s).
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select

from app.db.base import SessionLocal
from app.models.horario import Horario
from app.routers.usuarios import _hoy_local

CAMPOS = ("label", "hora_inicio1", "hora_fin1", "hora_inicio2", "hora_fin2")
TEMPORAL = {
    "label": "00:00-23:59",
    "hora_inicio1": "00:00",
    "hora_fin1": "23:59",
    "hora_inicio2": None,
    "hora_fin2": None,
}


def _de_hoy(db: Any, usuario_id: int, mes: int, anio: int, dia: int) -> list[Horario]:
    return list(
        db.scalars(
            select(Horario).where(
                Horario.usuario_id == usuario_id,
                Horario.mes == mes,
                Horario.anio == anio,
                Horario.dia_semana == dia,
            )
        ).all()
    )


def _borrar(usuario_id: int, mes: int, anio: int, dia: int) -> None:
    with SessionLocal() as db:
        for fila in _de_hoy(db, usuario_id, mes, anio, dia):
            db.delete(fila)
        db.commit()


def _crear(
    usuario_id: int, mes: int, anio: int, dia: int, datos: dict[str, Any]
) -> None:
    with SessionLocal() as db:
        db.add(
            Horario(
                usuario_id=usuario_id,
                mes=mes,
                anio=anio,
                dia_semana=dia,
                created_at=datetime.now(UTC),
                **datos,
            )
        )
        db.commit()


@contextmanager
def _turno_que_cubre_ahora(usuario_id: int) -> Iterator[None]:
    mes, anio, dia = _hoy_local()
    with SessionLocal() as db:
        respaldo = [
            {campo: getattr(fila, campo) for campo in CAMPOS}
            for fila in _de_hoy(db, usuario_id, mes, anio, dia)
        ]
    try:
        _borrar(usuario_id, mes, anio, dia)
        _crear(usuario_id, mes, anio, dia, TEMPORAL)
        yield
    finally:
        _borrar(usuario_id, mes, anio, dia)
        for datos in respaldo:
            _crear(usuario_id, mes, anio, dia, datos)


@pytest.fixture
def turno_ahora() -> Callable[[int], Any]:
    return _turno_que_cubre_ahora
