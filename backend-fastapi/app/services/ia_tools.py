"""Tools de Wilmercito con schemas estilo MCP.

Cada tool declara `name`, `description` y `parameters` (JSON Schema, compatible
MCP) y un `run` que usa los servicios internos con el contexto del usuario.
Hoy las invoca el router de intenciones determinista; el paso a un servidor MCP
real (stdio/HTTP) es exponer este mismo REGISTRO sin cambiar la lógica.
"""

from typing import Any

from app.services import ia_retrieval


def _tool_buscar(texto: str, top_k: int = 3) -> dict[str, Any]:
    return {"resultados": ia_retrieval.buscar(texto, top_k)}


def _tool_guiar_creacion() -> dict[str, Any]:
    doc = ia_retrieval.por_id("kb_nueva")
    return {
        "guia": doc["solucion"] if doc else "",
        "url": "/atenciones/nueva/",
        "fuente": "kb_nueva",
    }


REGISTRO: dict[str, dict[str, Any]] = {
    "buscar_atenciones": {
        "description": "Busca atenciones pasadas parecidas a un problema.",
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {"type": "string"},
                "top_k": {"type": "integer", "default": 3},
            },
            "required": ["texto"],
        },
        "run": _tool_buscar,
    },
    "guiar_creacion": {
        "description": "Devuelve la guía paso a paso para crear una atención.",
        "parameters": {"type": "object", "properties": {}},
        "run": lambda: _tool_guiar_creacion(),
    },
}


def ejecutar(nombre: str, argumentos: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ejecuta una tool por nombre. Lanza KeyError si no existe."""
    tool = REGISTRO[nombre]
    return tool["run"](**(argumentos or {}))
