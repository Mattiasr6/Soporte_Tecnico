from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sugerencia(Base):
    __tablename__: str = "Sugerencias"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    texto: Mapped[str] = mapped_column("Texto", String(1000), nullable=False)
    estado: Mapped[str] = mapped_column(
        "Estado", String(20), nullable=False, default="pendiente"
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
