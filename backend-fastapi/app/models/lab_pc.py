from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabPc(Base):
    __tablename__: str = "LabPcs"
    __table_args__: tuple[Any, ...] = (
        Index("IX_LabPcs_LaboratorioId", "LaboratorioId"),
        Index("IX_LabPcs_LaboratorioId_Pos", "LaboratorioId", "Fila", "Col"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    laboratorio_id: Mapped[int] = mapped_column(
        "LaboratorioId", Integer, ForeignKey("Laboratorios.Id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column("Nombre", String(50), nullable=False)
    fila: Mapped[int] = mapped_column("Fila", Integer, nullable=False, default=0)
    col: Mapped[int] = mapped_column("Col", Integer, nullable=False, default=0)
    activa: Mapped[bool] = mapped_column("Activa", Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
