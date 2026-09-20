"""GET /api/areas legacy: réplica exacta del AreasController .NET (RN-S2-02)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.atencion import Atencion

router = APIRouter(prefix="/api/areas", tags=["areas"])

EXTRA_AREAS = [
    "Asistente F.C.S.",
    "ADI (Academia de Idiomas)",
    "Archivos Contabilidad",
    "Laboratorios y gabinetes de Medicina",
    "Plaza UPDS",
    "Vicerrectorado Administrativo",
    "Sala 2 (Directorio)",
    "Sala 3 (Directorio)",
]

FALLBACK_AREAS = [
    "Archivo",
    "Aula B-02",
    "Aula B-05 MED",
    "Aula B-06",
    "Aula B-10",
    "Aula B-11",
    "Aula C-04",
    "Aula C-07",
    "Aula C-09",
    "Aula C-12",
    "Biblioteca",
    "Bienestar Estudiantil",
    "Caja",
    "CAP",
    "Contabilidad",
    "Coordinación Acad. FCS",
    "Directorio",
    "EIAG",
    "Laboratorios de Computo",
    "Marketing",
    "Publicidad",
    "Recepción",
    "Rectorado",
    "Registro",
    "Relaciones Públicas",
    "Sala de Docentes",
    "Sala de lectura",
    "Sala Magna",
    "Secretaria General",
    "Sistemas",
    "Talento Humano",
    "Vicerrectorado",
]


def _aulas(prefijo: str, n: int) -> list[str]:
    return [f"Aula {prefijo}-{i:02d}" for i in range(1, n + 1)]


@router.get("", response_model=list[str])
def get_areas(db: DbSession, user: CurrentUser):
    distintas = {
        r[0].strip()
        for r in db.execute(
            select(Atencion.area_solicitante).where(
                Atencion.area_solicitante.is_not(None),
                Atencion.area_solicitante != "",
            )
        ).all()
        if r[0].strip()
    }
    areas = sorted(
        distintas
        | set(EXTRA_AREAS)
        | set(_aulas("A", 12))
        | set(_aulas("B", 21))
        | set(_aulas("C", 20))
        | set(_aulas("D", 18))
        | set(_aulas("E", 5))
    )
    if len(areas) == 1:  # solo Plaza UPDS, sin datos reales
        return FALLBACK_AREAS
    return areas
