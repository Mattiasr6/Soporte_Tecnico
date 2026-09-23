from pydantic import BaseModel, ConfigDict


class HorarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    nombre: str
    label: str
    dia_semana: int
    hora_inicio1: str | None
    hora_fin1: str | None
    hora_inicio2: str | None
    hora_fin2: str | None
    mes: int
    anio: int


class AsignarIn(BaseModel):
    usuario_id: int
    dia_semana: int
    hora_inicio1: str | None = None
    hora_fin1: str | None = None
    hora_inicio2: str | None = None
    hora_fin2: str | None = None
    mes: int
    anio: int


class AsignarLoteIn(BaseModel):
    asignaciones: list[AsignarIn]


class CoberturaFranja(BaseModel):
    franja: str
    hora: str
    tecnicos: list[str]


class CoberturaOut(BaseModel):
    mes: int
    anio: int
    laborable: list[CoberturaFranja]
    sabado: list[CoberturaFranja]
