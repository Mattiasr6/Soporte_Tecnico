"""Servidor MCP de Soporte (Fase A). stdio + HTTP :8090 con api-key.

Uso stdio (Claude Desktop):
    {"mcpServers": {"soporte": {"command": ".../.venv/bin/python",
                                "args": ["-m", "app.mcp_soporte.server"],
                                "cwd": "<backend-fastapi>"}}}
Uso HTTP:
    MCP_TRANSPORT=http MCP_API_KEY=<key> .../.venv/bin/python -m app.mcp_soporte.server
"""

import os

from fastmcp import FastMCP

from app.mcp_soporte import tools_atenciones, tools_ia, tools_sistema

mcp = FastMCP("soporte")

# Atenciones (lectura + escritura con confirm)
mcp.tool(tools_atenciones.soporte_buscar_atenciones)
mcp.tool(tools_atenciones.soporte_get_atencion)
mcp.tool(tools_atenciones.soporte_crear_borrador)
mcp.tool(tools_atenciones.soporte_confirmar_creacion)
mcp.tool(tools_atenciones.soporte_actualizar_atencion)
mcp.tool(tools_atenciones.soporte_reclasificar)
# Sistema
mcp.tool(tools_sistema.soporte_stats)
mcp.tool(tools_sistema.soporte_stats_tecnico)
mcp.tool(tools_sistema.soporte_arbol_jerarquia)
mcp.tool(tools_sistema.soporte_areas)
mcp.tool(tools_sistema.soporte_usuarios)
mcp.tool(tools_sistema.soporte_horarios)
# IA
mcp.tool(tools_ia.soporte_ia_preguntar)
mcp.tool(tools_ia.soporte_ia_buscar)
mcp.tool(tools_ia.soporte_ia_calificar)
mcp.tool(tools_ia.soporte_ia_pendientes)
mcp.tool(tools_ia.soporte_ia_promover)
mcp.tool(tools_ia.soporte_ia_evaluar)


def main() -> None:
    if os.environ.get("MCP_TRANSPORT", "stdio") == "http":
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=int(os.environ.get("MCP_PORT", "8090")),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
