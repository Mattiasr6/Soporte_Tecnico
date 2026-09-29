# Slice 11 — MCP real + poderes con confirmación

## Objetivo

18 tools MCP + primeros poderes de escritura, siempre con confirmación humana.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `Creo que aún tenemos que pulir qué se tiene que guardar y qué realmente tiene que escribir. ¿Podríamos crearle un MCP con Python para que pueda usar los endpoints?`
> `Quiero que trabajes con specs. No las estás haciendo con GitNexus. Ver qué tan bien lo estamos haciendo.`
> `Implementemos` (Fase A)
> `Vamos con la fase B.`
> `Necesito darle más poderes y que siempre busque la confirmación del usuario.`

## Respuesta / acciones del agente

1. Inspiración medida: `Zammad-MCP` (catálogo+resources+prompts), `tanss` (237 tools).
2. Spec Sisyphus-ready `docs/specs/fase-a-mcp-server.md` (RN-01..04, Gherkin, DoD) → implementado `app/mcp_soporte/` (FastMCP, 18 tools, JWT passthrough, `confirm:true`).
3. GitNexus ordenó el caos: había 2 repos registrados con el mismo nombre y todo medía el repo viejo; se eliminó el registro stale, se reindexó; `preguntar` LOW (solo `evaluar` depende).
4. Fase B: flujo guiado crear-atención por chips con estado en el mensaje (stateless) → preview → "Sí, crear" → `create_batch` real con colaborador Wilmercito (usuario id 14 creado con clave aleatoria).
5. Más poderes, todos con preview+confirm: mi estado, anotar (firma `[fecha Wilmercito]`), anunciar (jefe), reclasificar, colaborador, eliminar propia (aviso irreversible), cambiar solución.
6. Tests atraparon 2 crashes de índices de regex antes de desplegar; e2e verificó cada poder con limpieza posterior (restaurado desde backup).

## Evidencia

- Commits `ef7822e`, `b5e803a`, `8bc7e7a`; `tests/test_ia_unit.py` 12+; spec aprobada con DoD verde

## Decisión / hallazgo

- Spec primero (contratos+DoD), implementar después; GitNexus antes de editar símbolos.
- Ninguna escritura sin "¿Confirmas?" + chip explícito.
