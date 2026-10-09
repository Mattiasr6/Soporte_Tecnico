from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditoriaCambio(Base):
    """Rastro de cambios esenciales (creaciones, ediciones, borrados).

    Solo un Jefe puede leerlo: los Encargados y Auxiliares gestionan los datos
    pero no ven quién qué tocó ni qué se borró.
    """

    __tablename__: str = "AuditoriaCambios"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    fecha: Mapped[datetime] = mapped_column("Fecha", DateTime(timezone=True))
    usuario_id: Mapped[int | None] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=True
    )
    # copiado en texto: sobrevive a cambios de cuenta y sirve de respaldo
    usuario_email: Mapped[str] = mapped_column(
        "UsuarioEmail", String(200), nullable=False, default=""
    )
    usuario_nombre: Mapped[str] = mapped_column(
        "UsuarioNombre", String(200), nullable=False, default=""
    )
    rol: Mapped[str] = mapped_column("Rol", String(50), nullable=False, default="")
    accion: Mapped[str] = mapped_column("Accion", String(50), nullable=False)
    entidad: Mapped[str] = mapped_column("Entidad", String(50), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column("EntidadId", Integer, nullable=True)
    detalle: Mapped[str] = mapped_column("Detalle", Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
