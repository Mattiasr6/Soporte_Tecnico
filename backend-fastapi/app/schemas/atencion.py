from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AtencionCreate(BaseModel):
    area_solicitante: str = ""
    grupo_padre_id: int | None = None
    grupo_id: int | None = None
    area_id: int | None = None
    medio_solicitud: str
    usuario_solicitante: str
    categoria: str
    descripcion: str
    solucion: str
    observaciones: str | None = None
    enlace_apoyo: str | None = None
    colaborador_id: int | None = None
    fecha_registro: date | None = None


class AtencionBatchIn(BaseModel):
    atenciones: list[AtencionCreate]


class AtencionBatchOut(BaseModel):
    registros_insertados: int


class AtencionUpdate(BaseModel):
    area_solicitante: str | None = None
    grupo_padre_id: int | None = None
    grupo_id: int | None = None
    area_id: int | None = None
    medio_solicitud: str | None = None
    usuario_solicitante: str | None = None
    categoria: str | None = None
    descripcion: str | None = None
    solucion: str | None = None
    observaciones: str | None = None
    enlace_apoyo: str | None = None
    colaborador_id: int | None = None
    fecha_registro: date | None = None


class JerarquiaAtencionIn(BaseModel):
    """Solo la clasificación: el jefe elige el área y los 3 FK se derivan de ella."""

    area_id: int


class AtencionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    usuario_nombre: str
    area_solicitante: str
    grupo_padre_id: int | None
    grupo_padre_nombre: str | None
    grupo_id: int | None
    grupo_nombre: str | None
    area_id: int | None
    area_nombre: str | None
    medio_solicitud: str
    usuario_solicitante: str
    categoria: str
    descripcion: str
    solucion: str
    observaciones: str | None
    enlace_apoyo: str | None
    colaborador_id: int | None
    colaborador_nombre: str | None
    fecha_registro: date
    fuera_de_turno: bool
    created_at: datetime


class PorTecnico(BaseModel):
    usuario_id: int
    display_name: str
    total: int


class PorCategoria(BaseModel):
    categoria: str
    total: int


class PorMes(BaseModel):
    anio: int
    mes: int
    total: int


class PorArea(BaseModel):
    area: str
    total: int


class PorMedio(BaseModel):
    medio: str
    total: int


class TipoSolicitante(BaseModel):
    tipo: str
    total: int


class CategoriaMes(BaseModel):
    categoria: str
    anio: int
    mes: int
    total: int


class NodoConteo(BaseModel):
    id: int
    nombre: str
    total: int
    padre_id: int | None = None
    grupo_id: int | None = None


class DiaTotal(BaseModel):
    fecha: date
    total: int


class FlujoSankey(BaseModel):
    medio: str
    categoria: str
    grupo_padre: str
    total: int


class TecnicoFuera(BaseModel):
    usuario_id: int
    display_name: str
    total: int
    fuera: int


class TecnicoCategoria(BaseModel):
    usuario_id: int
    display_name: str
    categoria: str
    total: int


class StatsOut(BaseModel):
    total: int
    fuera_de_turno: int
    por_tecnico: list[PorTecnico]
    por_categoria: list[PorCategoria]
    por_mes: list[PorMes]
    por_area: list[PorArea]
    por_medio: list[PorMedio]
    por_tipo_solicitante: list[TipoSolicitante]
    por_categoria_mes: list[CategoriaMes]
    por_padre: list[NodoConteo]
    por_grupo: list[NodoConteo]
    por_area_id: list[NodoConteo]
    por_dia: list[DiaTotal]
    flujo_sankey: list[FlujoSankey]
    por_tecnico_fuera: list[TecnicoFuera]
    por_tecnico_categoria: list[TecnicoCategoria]
    asistencias: list[PorTecnico]
