from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GrupoPadre(Base):
    __tablename__: str = "GruposPadres"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(
        "Nombre", String(50), unique=True, nullable=False
    )
    codigo: Mapped[str] = mapped_column(
        "Codigo", String(60), unique=True, nullable=False
    )
    descripcion: Mapped[str | None] = mapped_column(
        "Descripcion", String(200), nullable=True
    )
    orden: Mapped[int] = mapped_column("Orden", Integer, nullable=False)
