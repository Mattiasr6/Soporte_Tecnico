from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GrupoPadre(Base):
    __tablename__ = "GruposPadres"

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    Nombre: Mapped[str] = mapped_column(
        "Nombre", String(50), unique=True, nullable=False
    )
    Descripcion: Mapped[str | None] = mapped_column(
        "Descripcion", String(200), nullable=True
    )
    Orden: Mapped[int] = mapped_column("Orden", Integer, nullable=False)
