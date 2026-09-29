from pydantic import BaseModel, ConfigDict


class GrupoPadreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo: str
    descripcion: str | None
    orden: int


class GrupoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_padre_id: int
    nombre: str
    codigo: str
    activo: bool


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_padre_id: int
    grupo_id: int | None
    nombre: str
    codigo: str
    activo: bool


class AreaConversionOut(BaseModel):
    grupo_id: int
    atenciones_movidas: int
    area_eliminada: bool


class ArbolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    padres: list[GrupoPadreOut]
    grupos: list[GrupoOut]
    areas: list[AreaOut]


class GrupoPadreIn(BaseModel):
    nombre: str
    codigo: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class GrupoPadreUpd(BaseModel):
    nombre: str | None = None
    codigo: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class GrupoIn(BaseModel):
    nombre: str
    grupo_padre_id: int
    codigo: str | None = None
    activo: bool = True


class GrupoUpd(BaseModel):
    nombre: str | None = None
    grupo_padre_id: int | None = None
    codigo: str | None = None
    activo: bool | None = None


class AreaIn(BaseModel):
    nombre: str
    grupo_padre_id: int
    grupo_id: int | None = None
    codigo: str | None = None
    activo: bool = True


class AreaUpd(BaseModel):
    nombre: str | None = None
    grupo_padre_id: int | None = None
    grupo_id: int | None = None
    codigo: str | None = None
    activo: bool | None = None
    actualizar_texto_legado: bool = False
