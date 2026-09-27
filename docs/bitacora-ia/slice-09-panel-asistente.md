# Slice 09 — Panel Asistente (control solo jefes)

## Objetivo

Que los técnicos no vean IDs internos (`kb_identidad`) y los jefes tengan control sin Django-admin.

## Prompts

> `si mis compañeros de trabajo (los otros técnicos, utilizan a wilmercito) y ven esto: Fuente: kb_identidad (...) como podriamos mejorar el comportamiento del chat si no eres jefe, talves el admin de django deberiamos simularlo en una nueva pestaña del sidebar unicamente para controlar el asistente`

## Respuesta / acciones del agente

1. `fuente_label()`: `kb_*` → "Base de conocimiento", `atencion_N` → "Atención #N", `feedback_N` → "Conocimiento del equipo", etc. La burbuja muestra el label (el id crudo sigue en el JSON para debug).
2. Pestaña **Asistente** en sidebar (mismo gateo `can_dashboard` que Dashboard/Usuarios): KPIs (indexadas, p95, rechazos/hora, pendientes), botón Reindexar, link a Curar conocimiento.
3. Verificado: `/asistente/` 200 con link + botón; técnicos sin permiso ni la ven.

## Evidencia

- Commit `42c4f9c`; `asistente.html`, `context_processors.py` (nav_page), `_navbar.html`

## Decisión / hallazgo

- Separar lo visible (labels) de lo auditable (ids) por rol.
