from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Atencion(Base):
    __tablename__ = "Atenciones"
    __table_args__ = (
        Index("IX_Atenciones_UsuarioId", "UsuarioId"),
        Index("IX_Atenciones_FechaRegistro", "FechaRegistro"),
        Index("IX_Atenciones_GrupoPadreId", "GrupoPadreId"),
        Index("IX_Atenciones_GrupoId", "GrupoId"),
        Index("IX_Atenciones_AreaId", "AreaId"),
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    UsuarioId: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    GrupoPadreId: Mapped[int | None] = mapped_column(
        "GrupoPadreId", Integer, ForeignKey("GruposPadres.Id"), nullable=True
    )
    GrupoId: Mapped[int | None] = mapped_column(
        "GrupoId", Integer, ForeignKey("Grupos.Id"), nullable=True
    )
    AreaId: Mapped[int | None] = mapped_column(
        "AreaId", Integer, ForeignKey("Areas.Id"), nullable=True
    )
    AreaSolicitante: Mapped[str] = mapped_column(
        "AreaSolicitante", String(200), nullable=False
    )
    MedioSolicitud: Mapped[str] = mapped_column(
        "MedioSolicitud", String(50), nullable=False
    )
    UsuarioSolicitante: Mapped[str] = mapped_column(
        "UsuarioSolicitante", String(10), nullable=False
    )
    Categoria: Mapped[str] = mapped_column("Categoria", String(200), nullable=False)
    Descripcion: Mapped[str] = mapped_column(
        "Descripcion", String(1000), nullable=False
    )
    Solucion: Mapped[str] = mapped_column("Solucion", String(1000), nullable=False)
    Observaciones: Mapped[str | None] = mapped_column(
        "Observaciones", String(2000), nullable=True
    )
    EnlaceApoyo: Mapped[str | None] = mapped_column(
        "EnlaceApoyo", String(500), nullable=True
    )
    ColaboradorId: Mapped[int | None] = mapped_column(
        "ColaboradorId", Integer, ForeignKey("Usuarios.Id"), nullable=True
    )
    FueraDeTurno: Mapped[bool] = mapped_column(
        "FueraDeTurno", Boolean, nullable=False, default=False
    )
    FechaRegistro: Mapped[date] = mapped_column("FechaRegistro", Date, nullable=False)
    CreatedAt: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
