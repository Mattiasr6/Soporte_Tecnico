"""DB-driven lab category lookup (replaces the hardcoded set in categorias.py)."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.laboratorio import LabCategoria


def get_categorias_activas(db: Session) -> list[LabCategoria]:
    return list(
        db.scalars(
            select(LabCategoria)
            .where(LabCategoria.activa.is_(True))
            .order_by(LabCategoria.nombre)
        ).all()
    )


def buscar_categoria(db: Session, nombre: str) -> LabCategoria | None:
    """Case-insensitive strip-compare against DB rows; None when absent."""
    q = (nombre or "").strip().lower()
    if not q:
        return None
    for row in db.scalars(select(LabCategoria)).all():
        if row.nombre.strip().lower() == q:
            return row
    return None


def validar_categoria(db: Session, nombre: str) -> LabCategoria:
    """Resolve a category name to its row; 422 when unknown or inactive."""
    row = buscar_categoria(db, nombre)
    if row is None:
        raise HTTPException(
            status_code=422, detail=f"Categoria '{nombre}' no existe"
        )
    if not row.activa:
        raise HTTPException(
            status_code=422, detail=f"Categoria '{row.nombre}' inactiva"
        )
    return row
