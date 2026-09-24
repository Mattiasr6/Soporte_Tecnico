from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    __tablename__: str = "Usuarios"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        "Email", String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str | None] = mapped_column(
        "PasswordHash", String, nullable=True
    )
    display_name: Mapped[str] = mapped_column(
        "DisplayName", String(255), nullable=False
    )
    notas: Mapped[str | None] = mapped_column("Notas", Text, nullable=True)
    especialidad: Mapped[str | None] = mapped_column(
        "Especialidad", Text, nullable=True
    )
    role: Mapped[str] = mapped_column(
        "Role", String(50), nullable=False, default="Tecnico"
    )
    estado_actual: Mapped[str] = mapped_column(
        "EstadoActual", String(20), nullable=False, default="Ausente"
    )
    can_view_dashboard: Mapped[bool] = mapped_column(
        "CanViewDashboard", Boolean, nullable=False, default=False
    )
    activo: Mapped[bool] = mapped_column(
        "Activo", Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column("UpdatedAt", DateTime(timezone=True))
