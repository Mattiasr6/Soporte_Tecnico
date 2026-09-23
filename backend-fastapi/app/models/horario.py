from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Horario(Base):
    __tablename__: str = "Horarios"
    __table_args__: tuple[Any, ...] = (
        UniqueConstraint("UsuarioId", "Mes", "Anio", "DiaSemana"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    label: Mapped[str] = mapped_column("Label", String(100), nullable=False)
    hora_inicio1: Mapped[str | None] = mapped_column(
        "HoraInicio1", String(5), nullable=True
    )
    hora_fin1: Mapped[str | None] = mapped_column("HoraFin1", String(5), nullable=True)
    hora_inicio2: Mapped[str | None] = mapped_column(
        "HoraInicio2", String(5), nullable=True
    )
    hora_fin2: Mapped[str | None] = mapped_column("HoraFin2", String(5), nullable=True)
    dia_semana: Mapped[int] = mapped_column("DiaSemana", Integer, nullable=False)
    mes: Mapped[int] = mapped_column("Mes", Integer, nullable=False)
    anio: Mapped[int] = mapped_column("Anio", Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
