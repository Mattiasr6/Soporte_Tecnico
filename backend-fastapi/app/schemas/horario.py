from pydantic import BaseModel, ConfigDict


class HorarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    nombre: str
    label: str
    hora_inicio1: str | None
    hora_fin1: str | None
    hora_inicio2: str | None
    hora_fin2: str | None
    mes: int
    anio: int


class AsignarIn(BaseModel):
    usuario_id: int
    label: str
    hora_inicio1: str | None = None
    hora_fin1: str | None = None
    hora_inicio2: str | None = None
    hora_fin2: str | None = None
    mes: int
    anio: int


class CoberturaFranja(BaseModel):
    franja: str
    hora: str
    tecnicos: list[str]


class CoberturaOut(BaseModel):
    mes: int
    anio: int
    cobertura: list[CoberturaFranja]
