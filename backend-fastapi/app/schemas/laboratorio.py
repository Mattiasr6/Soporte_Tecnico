from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.atencion import PorCategoria, PorMes

__all__ = [
    "AuxiliarCreate",
    "AuxiliarEntry",
    "EquipoOut",
    "EquipoReplace",
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
    "PorTurno",
    "TurnoHorario",
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
    descripcion: str | None = None
    activa: bool


class LabCategoriaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None


class LabCategoriaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    activa: bool | None = None


class LabAtencionCreate(BaseModel):
    laboratorio_id: int
    categoria: str
    auxiliar_nombre: str = ""
    turno: str | None = None
    medio_solicitud: str | None = None
    descripcion: str
    solucion: str
    observaciones: str | None = None
    fecha_registro: date | None = None
    forzar_duplicado: bool = False


class LabAtencionUpdate(BaseModel):
    laboratorio_id: int | None = None
    categoria: str | None = None
    auxiliar_nombre: str | None = None
    turno: str | None = None
    medio_solicitud: str | None = None
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
    turno: str | None = None
    medio_solicitud: str | None = None
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


class PorTurno(BaseModel):
    turno: str
    total: int


class PorTurnoFuera(BaseModel):
    turno: str
    total: int
    fuera: int


class PorAuxiliarFuera(BaseModel):
    auxiliar: str
    turno: str
    fuera: int


class LabStatsOut(BaseModel):
    total: int
    por_lab: list[PorLab]
    por_categoria: list[PorCategoria]
    por_mes: list[PorMes]
    por_turno: list[PorTurno] = []
    fuera_por_turno: list[PorTurnoFuera] = []
    fuera_por_auxiliar: list[PorAuxiliarFuera] = []


class AuxiliarEntry(BaseModel):
    nombre: str
    activo: bool = True
    encargado: bool = False


class AuxiliarCreate(BaseModel):
    nombre: str


class EquipoOut(BaseModel):
    auxiliares: list[AuxiliarEntry] = []


class EquipoReplace(BaseModel):
    auxiliares: list[AuxiliarEntry] = []


class EncargadoIn(BaseModel):
    nombre: str
    encargado: bool = True


class TurnoHorario(BaseModel):
    inicio: str
    fin: str
    auxiliares: list[str] = []
