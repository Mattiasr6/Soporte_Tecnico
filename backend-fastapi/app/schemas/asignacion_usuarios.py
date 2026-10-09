"""Schemas for asignacion user management (old Supabase `perfiles` screen).

Identity lives in Soporte `Usuarios`; these schemas speak the asignacion rol
names and are translated in `routers/asignacion/usuarios.py`.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.asignacion_turnos import TurnoCodigo

RolAsignacion = Literal[
    "admin", "auxiliar", "decano", "encargado", "invitado", "tecnico"
]
# A new account always gets access (old fn_crear_usuario set, plus tecnico).
RolNuevo = Literal["admin", "auxiliar", "decano", "encargado", "tecnico"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UsuarioAsignacionOut(BaseModel):
    """A perfil joined with its Soporte user (`role` = Usuarios.Role)."""

    id: UUID
    usuario_id: int
    nombre_completo: str
    correo: str
    rol: RolAsignacion
    role: str
    activo: bool
    turno_habitual: TurnoCodigo | None
    sabado_rotativo: bool


class UsuarioAsignacionCreateIn(_In):
    # perfiles_textos_check: 1..120 chars after trim.
    nombre_completo: str = Field(max_length=120)
    correo: str = Field(max_length=255)
    password: str = Field(max_length=72)
    rol: RolNuevo


class UsuarioAsignacionUpdateIn(_In):
    """Only the fields sent are changed (`turno_habitual: null` clears it)."""

    nombre_completo: str | None = Field(default=None, max_length=120)
    rol: RolAsignacion | None = None
    activo: bool | None = None
    turno_habitual: TurnoCodigo | None = None
    sabado_rotativo: bool | None = None


class PasswordIn(_In):
    password: str = Field(max_length=72)
