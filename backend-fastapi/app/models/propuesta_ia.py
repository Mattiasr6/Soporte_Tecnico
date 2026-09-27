from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PropuestaIA(Base):
    __tablename__: str = "PropuestaIA"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    proponente_id: Mapped[int] = mapped_column(
        "ProponenteId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column("Tipo", String(50), nullable=False)
    payload: Mapped[str] = mapped_column("Payload", Text, nullable=False)
    estado: Mapped[str] = mapped_column(
        "Estado", String(20), nullable=False, default="pendiente"
    )
    atencion_id: Mapped[int | None] = mapped_column(
        "AtencionId", Integer, ForeignKey("Atenciones.Id"), nullable=True
    )
    revisor_id: Mapped[int | None] = mapped_column(
        "RevisorId", Integer, ForeignKey("Usuarios.Id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
