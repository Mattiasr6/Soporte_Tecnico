# Uso de OpenCode en este proyecto

## Método

Cada trabajo siguió el ciclo **prompt → respuesta → evidencia verificada**:
nada se aceptó por palabra; tests, evaluaciones y comandos se re-ejecutaron
antes de darlos por hechos. Decisiones y fracasos quedaron en memoria
persistente para no repetir errores.

Nota: el trabajo corrió sobre capas de delegación gratuitas y motor de
inferencia local abierto (Qwen2.5 GGUF en llama.cpp propio); ninguna llamada a
APIs de nube.

## Impacto por fase

| Fase | Qué aportó OpenCode | Evidencia |
|---|---|---|
| Rama limpia | Plan de `git rm` del legacy V1 con lista verificada por `grep` | `docs/bitacora-ia/slice-01` |
| Infra VM + DB | Instalación PG15, diagnóstico del dump PG16→PG15, corrección `DATABASE_URL` | `slice-02` |
| Motor llama.cpp | Flags CUDA sm_75, diagnóstico de puerto ocupado y de `pkill` que se auto-mataba | `slice-03` |
| Retrieval | `ia_retrieval.py` + `routers/ia.py`; detectó el umbral heredado roto y lo recalibró a 0.5 | `slice-04` |
| Burbuja chat | CSS, diagnóstico por capas (DOM→estilos→caché de templates) con Playwright | `slice-05` |
| Guardrails | Diseño en 3 capas tras medir el jailbreak del 1.5B; tests que atraparon 2 bugs | `slice-06` |
| Modelo 3B | Comparativa medida 1.5B vs 3B, rotación de api-key | `slice-07` |
| Aprendizaje | Loop 👍/👎 → `FeedbackIA` → promover → Chroma | `slice-08` |
| Panel + sistema | `fuente_label`, pestaña Asistente, intents SQL, híbrido BM25+RRF, MCP 18 tools | `slice-09`–`slice-11` |
| Humanidad | Saludo con nombre/hora, memoria de 4 turnos, tarjetas, turnos, informes | `slice-12` |
| Fine-tuning | Env QLoRA, dataset 2229 pares, 3 noches, diagnóstico honesto del 5/30 | `slice-13` |
| Producción | P0, backups, systemd, merge sin conflictos, deploy con evaluar 9/10 | `slice-14` |
| Revisión | Intento terminal honesto + evidencia sustituta; specs Fase 1 y 2 | `slice-15`, `docs/specs/` |

## Dónde está la transcripción completa

`docs/bitacora-ia/` (README + 15 slices): cada archivo trae Objetivo → Prompts
verbatim → Respuesta/acciones → Evidencia (commits, comandos, salidas) →
Decisión. El trabajo previo a esa sesión viene de handoffs (resumido, no verbatim).
Especificaciones de revisión: `docs/specs/revision-local-fase1.md` y `fase2.md`.
