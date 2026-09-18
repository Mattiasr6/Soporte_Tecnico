from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "Usuarios"

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    Email: Mapped[str] = mapped_column(
        "Email", String(255), unique=True, nullable=False
    )
    PasswordHash: Mapped[str | None] = mapped_column(
        "PasswordHash", String, nullable=True
    )
    DisplayName: Mapped[str] = mapped_column("DisplayName", String(255), nullable=False)
    Notas: Mapped[str | None] = mapped_column("Notas", Text, nullable=True)
    Especialidad: Mapped[str | None] = mapped_column(
        "Especialidad", Text, nullable=True
    )
    Role: Mapped[str] = mapped_column(
        "Role", String(50), nullable=False, default="Tecnico"
    )
    EstadoActual: Mapped[str] = mapped_column(
        "EstadoActual", String(20), nullable=False, default="Ausente"
    )
    CanViewDashboard: Mapped[bool] = mapped_column(
        "CanViewDashboard", Boolean, nullable=False, default=False
    )
    CreatedAt: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
    UpdatedAt: Mapped[datetime] = mapped_column("UpdatedAt", DateTime(timezone=True))
