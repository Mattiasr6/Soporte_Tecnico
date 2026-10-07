from pydantic import BaseModel


class SoftwareIn(BaseModel):
    nombre: str
    licencia: str = "gratuita"
    uso: str = ""
    esencial: bool = False
    docentes: bool = False
    activo: bool = True


class SoftwareOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nombre: str
    licencia: str = ""
    uso: str = ""
    esencial: bool = False
    docentes: bool = False
    activo: bool = True
    labs: list[int] = []


class PlantillaIn(BaseModel):
    nombre: str
    categoria: str = "SOFTWARE"
    descripcion: str = ""
    solucion: str = ""
    turno: str | None = None
    activa: bool = True


class PlantillaOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    nombre: str
    categoria: str = ""
    descripcion: str = ""
    solucion: str = ""
    turno: str | None = None
    activa: bool = True


class PcEstadoIn(BaseModel):
    software_id: int
    estado: str
    auxiliar_nombre: str = ""
    categoria: str = "SOFTWARE"


class LabSoftwareIn(BaseModel):
    software_ids: list[int] = []
