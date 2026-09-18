from pydantic import BaseModel, ConfigDict


class GrupoPadreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    orden: int


class GrupoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_padre_id: int
    nombre: str
    activo: bool


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_padre_id: int
    grupo_id: int | None
    nombre: str
    activo: bool


class ArbolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    padres: list[GrupoPadreOut]
    grupos: list[GrupoOut]
    areas: list[AreaOut]
