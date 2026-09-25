from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogIA(Base):
    __tablename__: str = "LogIA"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    pregunta: Mapped[str] = mapped_column("Pregunta", String(500), nullable=False)
    fuente: Mapped[str | None] = mapped_column(
        "Fuente", String(100), nullable=True
    )
    rechazado: Mapped[bool] = mapped_column(
        "Rechazado", Boolean, nullable=False, default=False
    )
    ms: Mapped[int] = mapped_column("Ms", Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
