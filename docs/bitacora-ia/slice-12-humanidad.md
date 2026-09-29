# Slice 12 — Humanidad (nombre, memoria, tarjetas, turnos)

## Objetivo

Que Wilmercito se sienta asistente, no grabadora.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `¿Cómo podríamos mejorar la humanidad de Wilmercito? ¿Qué mejoras nos faltan?`
> `VAMO A ELLO` (×2: tarjetas+saludo; turnos+comparativa)
> `¿Otro tipo de mejoras? Ya no se me ocurren demasiadas cosas.`
> `2` (sugerencia de solución al crear)

## Respuesta / acciones del agente

1. Saludo con nombre y hora La Paz; memoria de 4 turnos en sesión Django → prompt del modelo; contador de frustración (al 2do fallo ofrece derivar a un jefe).
2. KB con alias (`categorías`, `medios`...); limpieza de muletillas ("y…", "entonces…") antes de retrieval.
3. Tarjetas visuales (borde dorado Starbucks) para tickets/similares + saludo contextual con tu nombre (hora La Paz en JS).
4. Turnos en vivo (reusa `estado_efectivo`, "entra 14:30") + comparativa mes vs anterior.
5. Sugerencia de solución en *Nueva atención*: debounce 800ms → `/api/ia/buscar` → caja "Wilmercito sugiere" + "Usar como base" (solo si solución vacía; extrae línea `Solución:`).
6. Incidente real: primer test dio 500 por `ReadTimeout` (el timer nocturno había disparado reindex) → vista resiliente (`except Exception` → 502) + gate nocturno reordenado (evaluar ANTES de parar el server).

## Evidencia

- Commits `e773ae9`, `bc5ecfb`, `422f0eb`, `3c40ab8`; capturas Playwright con tarjeta verde Starbucks

## Decisión / hallazgo

- La "magia" es contexto: nombre, hora, memoria, tarjetas. Nada requiere un modelo más grande.
