from pydantic import BaseModel


class UsuarioOut(BaseModel):
    id: int
    display_name: str
    especialidad: str | None = None
    role: str
    estado_actual: str
    horario_hoy: str | None = None
    entra_a_las: str | None = None
    atenciones_hoy: int = 0
    puede_cambiar_estado: bool = False
    activo: bool = True


class UsuarioCreateIn(BaseModel):
    email: str
    display_name: str
    role: str
    password: str | None = None
    activo: bool = True


class ActivoIn(BaseModel):
    activo: bool


class RolIn(BaseModel):
    role: str


class PasswordResetIn(BaseModel):
    password: str


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


class SesionIn(BaseModel):
    conectado: bool
