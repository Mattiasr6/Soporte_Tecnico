from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Atencion(Base):
    __tablename__: str = "Atenciones"
    __table_args__: tuple[Any, ...] = (
        Index("IX_Atenciones_UsuarioId", "UsuarioId"),
        Index("IX_Atenciones_ColaboradorId", "ColaboradorId"),
        Index("IX_Atenciones_FechaRegistro", "FechaRegistro"),
        Index("IX_Atenciones_GrupoPadreId", "GrupoPadreId"),
        Index("IX_Atenciones_GrupoId", "GrupoId"),
        Index("IX_Atenciones_AreaId", "AreaId"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    grupo_padre_id: Mapped[int | None] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=True
    )
    grupo_id: Mapped[int | None] = mapped_column(
        "GrupoId", Integer, ForeignKey("Grupos.Id"), nullable=True
    )
    area_id: Mapped[int | None] = mapped_column(
        "AreaId", Integer, ForeignKey("Areas.Id"), nullable=True
    )
    area_solicitante: Mapped[str] = mapped_column(
        "AreaSolicitante", String(200), nullable=False
    )
    medio_solicitud: Mapped[str] = mapped_column(
        "MedioSolicitud", String(50), nullable=False
    )
    usuario_solicitante: Mapped[str] = mapped_column(
        "UsuarioSolicitante", String(10), nullable=False
    )
    categoria: Mapped[str] = mapped_column("Categoria", String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(
        "Descripcion", String(1000), nullable=False
    )
    solucion: Mapped[str] = mapped_column("Solucion", String(1000), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(
        "Observaciones", String(2000), nullable=True
    )
    enlace_apoyo: Mapped[str | None] = mapped_column(
        "EnlaceApoyo", String(500), nullable=True
    )
    colaborador_id: Mapped[int | None] = mapped_column(
        "ColaboradorId", Integer, ForeignKey("Usuarios.Id"), nullable=True
    )
    fuera_de_turno: Mapped[bool] = mapped_column(
        "FueraDeTurno", Boolean, nullable=False, default=False
    )
    fecha_registro: Mapped[date] = mapped_column("FechaRegistro", Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
