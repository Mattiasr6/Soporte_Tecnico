from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Software(Base):
    __tablename__: str = "Software"
    __table_args__: tuple[Any, ...] = (Index("IX_Software_Nombre", "Nombre"),)

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column("Nombre", String(200), nullable=False)
    licencia: Mapped[str] = mapped_column(
        "Licencia", String(50), nullable=False, default="gratuita"
    )
    uso: Mapped[str] = mapped_column("Uso", String(500), nullable=False, default="")
    esencial: Mapped[bool] = mapped_column(
        "Esencial", Boolean, nullable=False, default=False
    )
    docentes: Mapped[bool] = mapped_column(
        "Docentes", Boolean, nullable=False, default=False
    )
    activo: Mapped[bool] = mapped_column("Activo", Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))


class SoftwareLab(Base):
    __tablename__: str = "SoftwareLab"
    __table_args__: tuple[Any, ...] = (
        Index("IX_SoftwareLab_SoftwareId", "SoftwareId"),
        Index("IX_SoftwareLab_LaboratorioId", "LaboratorioId"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    software_id: Mapped[int] = mapped_column(
        "SoftwareId", Integer, ForeignKey("Software.Id"), nullable=False
    )
    laboratorio_id: Mapped[int] = mapped_column(
        "LaboratorioId", Integer, ForeignKey("Laboratorios.Id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))


class PcSoftware(Base):
    __tablename__: str = "PcSoftware"
    __table_args__: tuple[Any, ...] = (
        Index("IX_PcSoftware_PcId", "PcId"),
        Index("IX_PcSoftware_SoftwareId", "SoftwareId"),
    )

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    pc_id: Mapped[int] = mapped_column(
        "PcId", Integer, ForeignKey("LabPcs.Id"), nullable=False
    )
    software_id: Mapped[int] = mapped_column(
        "SoftwareId", Integer, ForeignKey("Software.Id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(
        "Estado", String(20), nullable=False, default="instalado"
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column("UpdatedAt", DateTime(timezone=True))


class LabPlantilla(Base):
    __tablename__: str = "LabPlantillas"
    __table_args__: tuple[Any, ...] = (Index("IX_LabPlantillas_Nombre", "Nombre"),)

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column("Nombre", String(100), nullable=False)
    categoria: Mapped[str] = mapped_column(
        "Categoria", String(200), nullable=False, default="SOFTWARE"
    )
    descripcion: Mapped[str] = mapped_column(
        "Descripcion", String(2000), nullable=False, default=""
    )
    solucion: Mapped[str] = mapped_column(
        "Solucion", String(2000), nullable=False, default=""
    )
    turno: Mapped[str | None] = mapped_column("Turno", String(20), nullable=True)
    activa: Mapped[bool] = mapped_column("Activo", Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True))
