from datetime import date, datetime

from pydantic import BaseModel


class NovedadOut(BaseModel):
    id: int
    usuario_id: int
    auxiliar_nombre: str
    tipo: str
    texto: str
    turno: str | None = None
    laboratorio_id: int | None = None
    laboratorio: str = ""
    tiene_foto: bool = False
    estado: str
    entregado_a: str | None = None
    fecha_registro: date
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class NovedadAccion(BaseModel):
    accion: str
    auxiliar_nombre: str | None = None
    entregado_a: str | None = None
