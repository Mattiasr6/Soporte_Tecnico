from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Grupo(Base):
    __tablename__: str = "Grupos"
    __table_args__: tuple[Any, ...] = (UniqueConstraint("GrupoPadreId", "Nombre"),)

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    grupo_padre_id: Mapped[int] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column("Nombre", String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(
        "Codigo", String(60), unique=True, nullable=False
    )
    activo: Mapped[bool] = mapped_column(
        "Activo", Boolean, nullable=False, default=True
    )
