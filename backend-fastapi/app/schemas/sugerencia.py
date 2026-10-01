from pydantic import BaseModel, Field


class SugerenciaIn(BaseModel):
    texto: str = Field(min_length=1, max_length=1000)


class SugerenciaPatchIn(BaseModel):
    estado: str


class SugerenciaOut(BaseModel):
    id: int
    usuario_id: int
    autor: str
    texto: str
    estado: str
    fecha: str
