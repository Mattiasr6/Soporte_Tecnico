"""Tools IA: envoltorios sobre los endpoints /api/ia/* existentes."""

from typing import Any

from .client import api


def soporte_ia_preguntar(jwt: str, pregunta: str) -> Any:
    """Pregunta a Wilmercito (RAG + guardrails)."""
    return api("POST", "/api/ia/preguntar", jwt, {"pregunta": pregunta})


def soporte_ia_buscar(jwt: str, texto: str, top_k: int = 3) -> Any:
    """Búsqueda semántica de casos (sin texto generado)."""
    return api("POST", "/api/ia/buscar", jwt, {"texto": texto, "top_k": top_k})


def soporte_ia_calificar(
    jwt: str, pregunta: str, respuesta: str, puntaje: int, fuente: str | None = None
) -> Any:
    """Califica una respuesta 1-4 (alimenta el loop de aprendizaje)."""
    return api(
        "POST",
        "/api/ia/calificar",
        jwt,
        {"pregunta": pregunta, "respuesta": respuesta, "puntaje": puntaje, "fuente": fuente},
    )


def soporte_ia_pendientes(jwt: str) -> Any:
    """Calificaciones por curar (jefe)."""
    return api("GET", "/api/ia/feedback", jwt)


def soporte_ia_promover(jwt: str, feedback_id: int) -> Any:
    """Promueve un feedback a la base (jefe)."""
    return api("POST", f"/api/ia/feedback/{feedback_id}/promover", jwt, {})


def soporte_ia_evaluar(jwt: str) -> Any:
    """Batería de 10 preguntas con latencia y fuente (jefe)."""
    return api("POST", "/api/ia/evaluar", jwt, {})
