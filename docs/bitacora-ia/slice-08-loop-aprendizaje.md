# Slice 08 — Loop de aprendizaje (👍/👎 → Chroma)

## Objetivo

Que Wilmercito aprenda de calificaciones, con curaduría humana (patrón del motor Adlux).

## Prompts

> (propuesta del agente tras "quiero que este asistente sea sorprendente")
> Diseño: burbuja con 👍/👎 → `FeedbackIA` → jefe promueve → Chroma.

## Respuesta / acciones del agente

1. Migración `0008` (`FeedbackIA`), endpoints `/ia/calificar`, `/ia/feedback` (jefe), `/ia/feedback/{id}/promover` (indexa `feedback_<id>`).
2. Burbuja con botones + hint ("¿Qué te pareció esta respuesta?").
3. Verificado e2e: calificar(4) → pendiente visible para jefe → promover → la pregunta recupera `feedback_1`.
4. Pregunta del usuario sobre el admin del otro motor → respuesta: sin Django-admin; el equivalente es vista `/conocimiento/` + Burbuja.

## Evidencia

- Commits + migración `0008_feedback_ia.py`
- E2E: `calificar ok → pendientes [(1,...)] → promover ok → fuente feedback_1`

## Decisión / hallazgo

- Loop cerrado sin admin pesado: voto (técnico) → cura (jefe) → índice.
