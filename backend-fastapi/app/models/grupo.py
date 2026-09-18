from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Grupo(Base):
    __tablename__ = "Grupos"
    __table_args__ = (UniqueConstraint("GrupoPadreId", "Nombre"),)

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    GrupoPadreId: Mapped[int] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=False
    )
    Nombre: Mapped[str] = mapped_column("Nombre", String(100), nullable=False)
    Activo: Mapped[bool] = mapped_column(
        "Activo", Boolean, nullable=False, default=True
    )
