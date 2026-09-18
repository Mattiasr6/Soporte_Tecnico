from pydantic import BaseModel


class UsuarioOut(BaseModel):
    id: int
    display_name: str
    especialidad: str | None = None
    role: str
    estado_actual: str


class EspecialidadIn(BaseModel):
    especialidad: str | None = None


class NotasIn(BaseModel):
    contenido: str | None = None


class NotasOut(BaseModel):
    contenido: str | None = None


class EstadoIn(BaseModel):
    estado_actual: str = "disponible"
    motivo: str | None = None
    colaborador_id: int | None = None
