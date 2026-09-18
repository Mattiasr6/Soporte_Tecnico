from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Area(Base):
    __tablename__ = "Areas"
    __table_args__ = (UniqueConstraint("GrupoPadreId", "GrupoId", "Nombre"),)

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    GrupoPadreId: Mapped[int] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=False
    )
    GrupoId: Mapped[int | None] = mapped_column(
        "GrupoId", Integer, ForeignKey("Grupos.Id"), nullable=True
    )
    Nombre: Mapped[str] = mapped_column("Nombre", String(200), nullable=False)
    Activo: Mapped[bool] = mapped_column(
        "Activo", Boolean, nullable=False, default=True
    )
