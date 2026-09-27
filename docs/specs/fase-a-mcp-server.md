---
title: "Fase A — MCP server real de Soporte (FastMCP)"
status: "approved"  # draft | approved | rejected
version: "1.0"
priority: "alta"
estimated_effort: "2-3 sesiones"
dependencies: ["rama dev_llama.cpp", "llama-server :8081 en host", "VM upds con PG15"]
---

### Historia de usuario

> **Como** técnico de soporte, **quiero** pedirle a Wilmercito acciones con herramientas
> (buscar, crear borrador, estadísticas) **para** resolver atenciones sin salir del chat.

### Objetivo

Exponer el sistema como servidor MCP real (stdio + HTTP) con 12 tools, sin bypass de roles.

---

## Stack Tecnológico (OBLIGATORIO)

| Capa | Tecnología | Versión | Notas |
|------|-----------|---------|-------|
| MCP server | FastMCP (Python) | v2.x | stdio + HTTP Streamable :8090 en VM |
| Backend consumido | FastAPI existente | — | tools llaman a `http://127.0.0.1:5012` |
| Auth | JWT del técnico (passthrough) | — | cero bypass; `is_privileged` se respeta |
| Retrieval | Chroma + multilingual-MiniLM | — | reutiliza `ia_retrieval` |
| LLM cliente | llama-server Qwen2.5-3B | :8081 host | solo para redactar con contexto |

## Arquitectura

### Diagrama de componentes (textual)

```
[Burbuja/MCP client] --stdio/HTTP--> [mcp_soporte :8090] --HTTP+JWT--> [FastAPI :5012]
        |                                                                    |
        +-- ia_tools (schemas)                                               +-- PG15 + Chroma
```

### Mapa de archivos

```
# Archivos a crear:
backend-fastapi/app/mcp_soporte/__init__.py      # registro y app FastMCP
backend-fastapi/app/mcp_soporte/server.py        # main stdio/HTTP + api-key
backend-fastapi/app/mcp_soporte/tools_atenciones.py  # buscar/get/crear-borrador/confirmar/actualizar/reclasificar
backend-fastapi/app/mcp_soporte/tools_sistema.py     # stats, jerarquía, usuarios, horarios
backend-fastapi/app/mcp_soporte/tools_ia.py          # preguntar/calificar/promover/evaluar (envuelven ia.py)
backend-fastapi/requirements.txt                 # +fastmcp (modificar)
docs/specs/fase-a-mcp-server.md                  # esta spec

# Archivos a modificar: ninguno existente (solo suma).
```

## Contratos de Datos

### Tools (request / response)

```python
# soporte_buscar_atenciones
{"texto": str, "top_k": int = 3}
# -> {"resultados": [{"id": "atencion_94", "descripcion": str, "distancia": float}]}

# soporte_crear_borrador (NO guarda)
{"descripcion": str, "categoria": str, "area_solicitante": str, ...}
# -> {"preview": {...}, "requiere_confirm": True}

# soporte_confirmar_creacion (GUARDA; exige confirm:true + JWT válido)
{"borrador": {...}, "confirm": True}
# -> {"id": int, "colaborador": "Wilmercito"}

# soporte_stats_tecnico
{"nombre": str}  # matching por tokens normalizados
# -> {"display_name": str, "total": int, "mes": int, "top_categorias": [...]}
```

### Reglas de Negocio

1. **RN-01:** Toda escritura exige `confirm:true` explícito del humano.
2. **RN-02:** Toda escritura lleva `colaborador_id` = Wilmercito (id 14); el autor es el dueño del JWT.
3. **RN-03:** Sin JWT válido → 401; sin privilegio en rutas de jefe → 403 (mismo `is_privileged`).
4. **RN-04:** Lectura nunca inventa: sin evidencia → `sin_evidencia:true` (no texto generado).

## Flujo Principal — crear atención desde el chat

1. Técnico: "crea la atención: impresora B-05 no imprime"
2. `soporte_crear_borrador` → preview + "¿confirmas? [Sí]"
3. Técnico: "sí"
4. `soporte_confirmar_creacion{confirm:true}` con su JWT → POST /api/atenciones/batch
5. Respuesta: "Creada #3120 a tu nombre, colaborador Wilmercito"

### Flujo Alternativo — sin confirmación

1. Si `confirm` falta o es falso → 400 `"requiere_confirm"` (nada se guarda).

### Flujo de Error

| Condición | Respuesta | Status | Mensaje |
|-----------|-----------|--------|---------|
| Sin JWT | Auth Error | 401 | "Falta token Bearer" |
| Técnico pide ruta de jefe | Forbidden | 403 | "Solo un jefe puede…" |
| Motor IA caído (solo tools IA) | Degraded | 503 | "motor-ia-no-disponible" |

## Catálogo de Errores

| Código | HTTP | Condición | Mensaje visible | Log |
|--------|------|-----------|----------------|-----|
| MCP-001 | 401 | sin JWT | "Falta token Bearer" | warn |
| MCP-002 | 403 | sin privilegio | "Solo un jefe puede…" | warn |
| MCP-003 | 400 | escritura sin confirm | "requiere_confirm" | info |
| MCP-004 | 503 | llama-server caído | "motor-ia-no-disponible" | error |

## Criterios de Aceptación (Gherkin)

```gherkin
Feature: MCP Soporte

  Scenario: Crear atención con confirmación
    Given JWT de técnico válido
    When creo borrador y luego confirmo con confirm:true
    Then la atención existe con mi autoría y colaborador Wilmercito

  Scenario: Sin confirmación no guarda
    Given un borrador válido
    When confirmo sin confirm:true
    Then 400 requiere_confirm y nada se crea

  Scenario: Inspector lista tools
    When abro el inspector MCP contra :8090
    Then veo 12+ tools con schemas
```

## Mockups ASCII — panel Asistente (ya existe, solo sumar)

```
+--------------------------------------------------+
| Wilmercito · control                             |
| [Docs: 2845] [Motor: ok] [Por curar: N]          |
| [Reindexar] [Curar conocimiento] [Ver tools MCP] |
+--------------------------------------------------+
```

## Definition of Done (DoD)

1. [x] Inspector MCP lista 12+ tools con schemas válidos (18 verificados vía `list_tools`)
2. [x] Borrador → confirmar crea atención real con colaborador Wilmercito (e2e id 3768, limpiado)
3. [x] Sin confirm no se guarda (MCP-003 verificado: `requiere_confirm`)
4. [x] 401/403 con JWT ausente o rol insuficiente (passthrough, sin bypass)
5. [x] `POST /ia/evaluar` sigue 10/10 sin regresiones
6. [x] `gitnexus_impact(preguntar)` LOW; `wilmercito_vista` LOW
7. [x] Rama limpia, docs actualizadas

## Orden de Implementación

1. **Paso 1:** `mcp_soporte/` + server stdio/HTTP — `server.py`
2. **Paso 2:** tools lectura (usan endpoints existentes) — `tools_atenciones.py(R)`, `tools_sistema.py`
3. **Paso 3:** tools escritura con confirm — `tools_atenciones.py(W)`
4. **Paso 4:** tools IA (envoltorios) — `tools_ia.py`
5. **Paso 5:** e2e en VM + inspector + commit

## Lo que NO está en alcance (explícito)

- ❌ Function-calling directo del 3B (no fiable; los intents llaman tools)
- ❌ Escritura sin confirmación humana
- ❌ Cambiar permisos/roles existentes
