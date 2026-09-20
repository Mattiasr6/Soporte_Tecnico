from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Area(Base):
    __tablename__: str = "Areas"
    __table_args__: tuple[Any, ...] = (
        UniqueConstraint("GrupoPadreId", "GrupoId", "Nombre"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    grupo_padre_id: Mapped[int] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=False
    )
    grupo_id: Mapped[int | None] = mapped_column(
        "GrupoId", Integer, ForeignKey("Grupos.Id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column("Nombre", String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(
        "Activo", Boolean, nullable=False, default=True
    )
