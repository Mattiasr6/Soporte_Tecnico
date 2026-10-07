from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Novedad(Base):
    __tablename__: str = "Novedades"
    __table_args__: tuple[Any, ...] = (
        Index("IX_Novedades_Tipo", "Tipo"),
        Index("IX_Novedades_UsuarioId", "UsuarioId"),
        Index("IX_Novedades_Estado", "Estado"),
        Index("IX_Novedades_FechaRegistro", "FechaRegistro"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    auxiliar_nombre: Mapped[str] = mapped_column(
        "AuxiliarNombre", String(255), nullable=False
    )
    tipo: Mapped[str] = mapped_column("Tipo", String(20), nullable=False)
    texto: Mapped[str] = mapped_column("Descripcion", String(2000), nullable=False)
    turno: Mapped[str | None] = mapped_column("Turno", String(20), nullable=True)
    laboratorio_id: Mapped[int | None] = mapped_column(
        "LaboratorioId", Integer, ForeignKey("Laboratorios.Id"), nullable=True
    )
    foto_path: Mapped[str | None] = mapped_column(
        "FotoPath", String(500), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        "Estado", String(20), nullable=False, default="publicado"
    )
    entregado_a: Mapped[str | None] = mapped_column(
        "EntregadoA", String(255), nullable=True
    )
    fecha_registro: Mapped[date] = mapped_column("FechaRegistro", Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
