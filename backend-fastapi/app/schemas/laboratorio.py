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
    procesador: str | None = None
    ram: str | None = None
    disco: str | None = None
    marca: str | None = None
    gpu: str | None = None
    monitores: str | None = None
    sillas: int | None = None
    capacidad: int | None = None
    pcs_estudiantes: int | None = None
    pcs_docentes: int | None = None


class LaboratorioCreate(BaseModel):
    codigo: str
    nombre: str


class LaboratorioUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    activa: bool | None = None
    procesador: str | None = None
    ram: str | None = None
    disco: str | None = None
    marca: str | None = None
    gpu: str | None = None
    monitores: str | None = None
    sillas: int | None = None
    capacidad: int | None = None
    pcs_estudiantes: int | None = None
    pcs_docentes: int | None = None


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
    pc_nombre: str | None = None


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
    pc_nombre: str | None = None
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
    usuario_id: int | None = None


class AuxiliarCreate(BaseModel):
    nombre: str


class EquipoOut(BaseModel):
    auxiliares: list[AuxiliarEntry] = []


class EquipoReplace(BaseModel):
    auxiliares: list[AuxiliarEntry] = []


class VinculoIn(BaseModel):
    nombre: str
    usuario_id: int | None = None


class MiembroYoOut(BaseModel):
    nombre: str
    encargado: bool
    activo: bool


class EncargadoIn(BaseModel):
    nombre: str
    encargado: bool = True


class TurnoHorario(BaseModel):
    inicio: str
    fin: str
    auxiliares: list[str] = []


class LabPcIn(BaseModel):
    nombre: str
    fila: int = 0
    col: int = 0
    activa: bool = True


class LabPcsIn(BaseModel):
    filas: int = 0
    cols: int = 0
    pcs: list[LabPcIn] = []
