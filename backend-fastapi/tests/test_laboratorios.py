"""Foundation tests for laboratorios service (Fase 1): models + migration only."""

import inspect
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

from app.db.base import SessionLocal, engine
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
