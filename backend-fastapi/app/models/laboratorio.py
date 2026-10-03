from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Laboratorio(Base):
    __tablename__: str = "Laboratorios"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(
        "Codigo", String(20), unique=True, nullable=False
    )
    nombre: Mapped[str] = mapped_column("Nombre", String(200), nullable=False)
    activa: Mapped[bool] = mapped_column(
        "Activa", Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))


class LabCategoria(Base):
    __tablename__: str = "LabCategorias"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(
        "Nombre", String(200), unique=True, nullable=False
    )
    descripcion: Mapped[str | None] = mapped_column(
        "Descripcion", String(2000), nullable=True
    )
    activa: Mapped[bool] = mapped_column(
        "Activa", Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))


class LabAtencion(Base):
    __tablename__: str = "LabAtenciones"
    __table_args__: tuple[Any, ...] = (
        Index("IX_LabAtenciones_LaboratorioId", "LaboratorioId"),
        Index("IX_LabAtenciones_CategoriaId", "CategoriaId"),
        Index("IX_LabAtenciones_UsuarioId", "UsuarioId"),
        Index("IX_LabAtenciones_FechaRegistro", "FechaRegistro"),
        Index("IX_LabAtenciones_Turno", "Turno"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "UsuarioId", Integer, ForeignKey("Usuarios.Id"), nullable=False
    )
    laboratorio_id: Mapped[int] = mapped_column(
        "LaboratorioId", Integer, ForeignKey("Laboratorios.Id"), nullable=False
    )
    categoria_id: Mapped[int] = mapped_column(
        "CategoriaId", Integer, ForeignKey("LabCategorias.Id"), nullable=False
    )
    auxiliar_nombre: Mapped[str] = mapped_column(
        "AuxiliarNombre", String(255), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(
        "Descripcion", String(1000), nullable=False
    )
    solucion: Mapped[str] = mapped_column("Solucion", String(1000), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(
        "Observaciones", String(2000), nullable=True
    )
    fuera_de_turno: Mapped[bool] = mapped_column(
        "FueraDeTurno", Boolean, nullable=False, default=False
    )
    turno: Mapped[str | None] = mapped_column("Turno", String(20), nullable=True)
    medio_solicitud: Mapped[str | None] = mapped_column(
        "MedioSolicitud", String(50), nullable=True, default="Presencial"
    )
    fecha_registro: Mapped[date] = mapped_column("FechaRegistro", Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
