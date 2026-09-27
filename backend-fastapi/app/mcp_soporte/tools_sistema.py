"""Tools de lectura del sistema: stats, jerarquía, usuarios, horarios."""

from typing import Any

from .client import api


def soporte_stats(jwt: str) -> Any:
    """Totales del sistema (usa endpoint existente)."""
    return api("GET", "/api/atenciones/stats", jwt)


def soporte_stats_tecnico(jwt: str, nombre: str) -> Any:
    """Estadísticas de un técnico por nombre (matching por tokens)."""
    from app.db.session import SessionLocal
    from app.routers.ia import _estadisticas_tecnico

    with SessionLocal() as db:
        return _estadisticas_tecnico(db, nombre)


def soporte_arbol_jerarquia(jwt: str) -> Any:
    """Árbol padres → grupos → áreas."""
    return api("GET", "/api/jerarquia/arbol", jwt)


def soporte_areas(jwt: str) -> Any:
    """Lista de áreas válidas."""
    return api("GET", "/api/areas", jwt)


def soporte_usuarios(jwt: str) -> Any:
    """Usuarios del sistema (según rol del JWT)."""
    return api("GET", "/api/usuarios", jwt)


def soporte_horarios(jwt: str, mes: int, anio: int) -> Any:
    """Horarios de un mes."""
    return api("GET", f"/api/horarios?mes={mes}&anio={anio}", jwt)
