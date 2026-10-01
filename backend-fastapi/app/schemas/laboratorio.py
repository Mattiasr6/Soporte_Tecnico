from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.atencion import PorCategoria, PorMes

__all__ = [
    "LabAtencionCreate",
    "LabAtencionOut",
    "LabAtencionUpdate",
    "LabCategoriaCreate",
    "LabCategoriaOut",
    "LabCategoriaUpdate",
    "LabStatsOut",
    "LaboratorioCreate",
    "LaboratorioOut",
    "LaboratorioUpdate",
    "PorCategoria",
    "PorLab",
    "PorMes",
]


class LaboratorioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    activa: bool


class LaboratorioCreate(BaseModel):
    codigo: str
    nombre: str


class LaboratorioUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    activa: bool | None = None


class LabCategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activa: bool


class LabCategoriaCreate(BaseModel):
    nombre: str


class LabCategoriaUpdate(BaseModel):
    nombre: str | None = None
    activa: bool | None = None


class LabAtencionCreate(BaseModel):
    laboratorio_id: int
    categoria: str
    auxiliar_nombre: str = ""
    descripcion: str
    solucion: str
    observaciones: str | None = None
    fecha_registro: date | None = None


class LabAtencionUpdate(BaseModel):
    laboratorio_id: int | None = None
    categoria: str | None = None
    auxiliar_nombre: str | None = None
    descripcion: str | None = None
    solucion: str | None = None
    observaciones: str | None = None
    fecha_registro: date | None = None


class LabAtencionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    usuario_nombre: str = ""
    laboratorio_id: int
    laboratorio: str = ""
    categoria_id: int
    categoria: str = ""
    auxiliar_nombre: str
    descripcion: str
    solucion: str
    observaciones: str | None = None
    fuera_de_turno: bool
    fecha_registro: date
    created_at: datetime


class PorLab(BaseModel):
    laboratorio_id: int
    laboratorio: str
    total: int


class LabStatsOut(BaseModel):
    total: int
    por_lab: list[PorLab]
    por_categoria: list[PorCategoria]
    por_mes: list[PorMes]
