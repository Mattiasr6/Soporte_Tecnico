from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Horario(Base):
    __tablename__ = "Horarios"
    __table_args__ = (UniqueConstraint("UsuarioId", "Mes", "Anio"),)

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    UsuarioId: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    Label: Mapped[str] = mapped_column("Label", String(100), nullable=False)
    HoraInicio1: Mapped[str | None] = mapped_column(
        "HoraInicio1", String(5), nullable=True
    )
    HoraFin1: Mapped[str | None] = mapped_column("HoraFin1", String(5), nullable=True)
    HoraInicio2: Mapped[str | None] = mapped_column(
        "HoraInicio2", String(5), nullable=True
    )
    HoraFin2: Mapped[str | None] = mapped_column("HoraFin2", String(5), nullable=True)
    Mes: Mapped[int] = mapped_column("Mes", Integer, nullable=False)
    Anio: Mapped[int] = mapped_column("Anio", Integer, nullable=False)
    CreatedAt: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
