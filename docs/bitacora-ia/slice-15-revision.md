# Slice 15 — Revisión formal (intento terminal honesto)

## Objetivo

Pasar la revisión nativa (receipt-driven) a la rama, en slices si hacía falta.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> (Hook del sistema: candidato sin revisar `sha256:c4d99...`)
> `Slices revisables` (×2, del usuario)

## Respuesta / acciones del agente

1. Preflight + START del candidato completo → consentimiento `granted` → terminal
   `lens_context_budget_exceeded` (287 archivos / 70158 líneas). Sin autoridad creada.
2. Estrategia slices: historial propio en 7 grupos contiguos (49 commits).
   Worktree en punta del slice 1 + STATUS → candidato 226 archivos / 43681 líneas
   (la base la fija el proveedor en el merge-base con `main`, que arrastra toda la
   historia de `dev`: S1–S10, v2, Django).
3. Consentimiento del slice 1 → `granted` → terminal otra vez por presupuesto.
4. Verificación de salida: `main` no contiene `backend-fastapi` → rebasar mi trabajo
   sobre `main` es imposible sin romperlo. Worktree de prueba eliminado.

## Evidencia

- `lens_context_budget_exceeded`, `mutation_outcome: not_started`, `next_action: stop` (×2)
- `git log dev..dev_llama.cpp`: 49 commits; `dev..dev_llama.cpp --stat`: 171 archivos
- Lineages: `review-1fa0ce21c70bd3b5`, `review-4c7dd7b0cf7b3fa5` (sin autoridad quemada)

## Decisión / hallazgo

- La revisión nativa no puede cubrir ramas con historia acumulada grande: el presupuesto
  se mide sobre el árbol candidato completo, no por commit.
- Evidencia sustituta para la defensa: 13 tests verdes, `/ia/evaluar` 10/10, bitácora
  14+1 slices, batería de 30 casos, gates que frenaron 3 despliegues rotos.
- Hacer `rebase` la víspera de la defensa para complacer a la herramienta sería
  imprudente; se deja constancia en vez de forzarla.
