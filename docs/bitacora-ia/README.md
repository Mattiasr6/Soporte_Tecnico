# Bitácora de la IA — Wilmercito (`dev_llama.cpp`)

Defensa: prompts usados en OpenCode + respuestas/acciones + evidencia, paso a paso.
Cobertura honesta: esta sesión está **verbatim** (cada prompt tal cual se escribió);
el trabajo previo a esta sesión viene de handoffs y memoria (resumido, no verbatim).

## Slices (un archivo por slice, en orden cronológico)

| # | Slice | Qué demuestra |
|---|-------|---------------|
| 01 | `slice-01-rama-limpia.md` | Crear rama, verificar `dev`, limpiar legacy V1 |
| 02 | `slice-02-infra-vm-db.md` | SSH sin password, PostgreSQL en VM, backup/restore |
| 03 | `slice-03-llamacpp-gpu.md` | Compilar llama.cpp CUDA, modelo Qwen, server con api-key |
| 04 | `slice-04-fase1-retrieval.md` | Endpoints `/ia/*`, Chroma, calibración de umbral |
| 05 | `slice-05-burbuja-chat.md` | Burbuja Wilmercito, burbuja invisible (CSS), burbuja visible |
| 06 | `slice-06-guardrails.md` | Jailbreak que cuenta chistes → defensa en 3 capas |
| 07 | `slice-07-modelo-3b.md` | 1.5B vs 3B medido, rechazo exacto |
| 08 | `slice-08-loop-aprendizaje.md` | 👍/👎 → FeedbackIA → jefe promueve → Chroma |
| 09 | `slice-09-panel-asistente.md` | Pestaña Asistente, fuentes amigables, /conocimiento |
| 10 | `slice-10-todo-el-sistema.md` | Usuarios, áreas, estadísticas SQL, BM25+RRF |
| 11 | `slice-11-mcp-poderes.md` | MCP 18 tools, poderes con confirmación, usuario Wilmercito |
| 12 | `slice-12-humanidad.md` | Nombre, hora, memoria, empatía, tarjetas, turnos, informes |
| 13 | `slice-13-finetuning.md` | 3 noches, 5/30, diagnóstico + plan (resultado negativo honesto) |
| 14 | `slice-14-produccion.md` | P0, backups, systemd, tests, credenciales, merge, deploy |

## Cómo leer cada slice

Cada archivo tiene: **Objetivo** → **Prompts** (verbatim, con `>` quote) →
**Respuesta/acciones del agente** → **Evidencia** (commits, comandos, salidas) →
**Decisión/hallazgo**.
