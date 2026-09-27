from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedbackIA(Base):
    __tablename__: str = "FeedbackIA"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    pregunta: Mapped[str] = mapped_column("Pregunta", String(500), nullable=False)
    respuesta: Mapped[str] = mapped_column("Respuesta", String(2000), nullable=False)
    fuente: Mapped[str | None] = mapped_column(
        "Fuente", String(100), nullable=True
    )
    puntaje: Mapped[int] = mapped_column("Puntaje", Integer, nullable=False)
    promovido: Mapped[bool] = mapped_column(
        "Promovido", Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
