# DOCUMENTACION.md — Decisiones técnicas y arquitectura

## 1. Arquitectura

```
┌─ HOST server-mattias (GPU) ─────────────────┐
│ llama.cpp GGML_CUDA (sm_75, RTX 2060 6 GB)  │
│ qwen2.5-3b-instruct-q4_k_m.gguf (2.0 GB)    │
│ llama-server :8081 (OpenAI-compatible, api-key; ufw solo VM) │
└──────────────────┬──────────────────────────┘
                   │ Tailscale
┌─ VM upds (Debian 12) ───────────────────────┐
│ PostgreSQL 15 :5432 (soporte / soporte_dev) │
│ backend-fastapi :5012 (endpoints /api/ia/*) │
│ frontend-django :8011 (burbuja Wilmercito)  │
│ Chroma ./chroma_db (CPU) + reglas en código │
└─────────────────────────────────────────────┘
```

Flujo de pregunta: burbuja → `POST /wilmercito/` (Django, con JWT de sesión; el
JWT nunca sale al navegador) → `POST /api/ia/preguntar` → intent exacto o
embedding + top-3 Chroma → `POST :8081/v1/chat/completions` → respuesta con `fuente`.

Índice: 2886 documentos (319 prod + 2494 histórico + KB estática `kb_*` +
usuarios/áreas/feedback promovido). Embeddings `paraphrase-multilingual-MiniLM-L12-v2`
**normalizados** (distancia coseno 0–2); umbral 0.5 calibrado con datos propios,
sugerencia marcada "no verificado" hasta 0.9.

## 2. Decisiones

| Decisión | Por qué |
|---|---|
| **llama.cpp directo, sin Ollama** | Ollama embebe llama.cpp; el servidor directo da control total (system por request, api-key, `-ngl 99`, temperatura 0.1) y es bonus track documentado |
| Modelo Qwen2.5-3B sobre 1.5B | Medido: el 1.5B parafraseaba el rechazo y contaba chistes ante jailbreak; el 3B devuelve el rechazo exacto (2168 MiB VRAM, ~140 tok/s) |
| Restricción en código, no en prompt | El modelo solo redacta; qué responder/permitir/guardar lo decide código determinista testeado |
| Intents exactos antes que modelo | Saludos, identidad, estadísticas, turnos, informes van por regex+SQL: rápido y 100 % fiable |
| Reranker cross-encoder OFF | Medido: ordenaba la KB exacta 6ta/12; el bi-encoder calibrado gana en este dominio |
| FT no desplegado | Eval 5/30 tres noches → el gate frenó el despliegue; base intacta en producción |
| Sin `rebase` pre-defensa | La revisión nativa pedía rebasar 49 commits sobre `main`; constancia en vez de forzarla |

## 3. Patrones aplicados

- **Service layer**: `app/services/` (`ia_retrieval`, `ia_tools`, `categorias`, `horarios`,
  `estados`) separa dominio de transporte; los routers solo validan y delegan.
- **Guardrails en capas** (defensa en profundidad): prefiltro regex jailbreak →
  system + `Context/Question/Answer` → postfiltro de marcadores + umbral.
- **Strategy por intención**: `_preguntar_impl` despacha a estrategias
  (`_estadisticas`, `_informe` por técnico/área/medio/categoría, `_turno_ahora`,
  `_comparativa_mes`, poderes con chip de confirmación); el registro
  `ia_tools.REGISTRO` + `ejecutar()` despacha tools por nombre con schemas JSON.
- **RBAC + auditoría**: escritura solo con confirmación explícita y rol
  (`is_privileged`, `_puede_dashboard`); cada pregunta se registra en `LogIA`
  (fuente, rechazo, ms); etiquetas legibles por rol (`fuente_label`).
- **Loop de aprendizaje supervisado**: 👍/👎 → `FeedbackIA` → el jefe promueve →
  `feedback_<id>` entra a Chroma. Nada aprende solo.

## 4. Contratos y errores

`POST /api/ia/buscar {texto, top_k}` → `{resultados[], sin_evidencia}` (umbral 0.5).
`POST /api/ia/preguntar {pregunta, historial[≤4]}` → `{respuesta, fuente, rechazado}`.
`POST /api/ia/reindexar` → `{nuevas, total}` (idempotente). `GET /api/ia/estado`,
`POST /api/ia/evaluar` (batería de 10, solo jefes), `GET /api/ia/resumen` (panel).

Errores: `503 motor-ia-no-disponible` (motor caído) · `200 rechazado:true` + mensaje
exacto (jailbreak/fuera-de-tema) · `200 "No tengo ese dato disponible."` (sin evidencia).

## 5. Calidad y operación

Tests: 13 unitarios IA (intents, guardrails, labels; sin GPU/DB) + suites RISK
(6, `review_risk.py`) y SLICE (5, `review_slices.py`); `/ia/evaluar` 10/10 en
desarrollo y 9/10 en deploy (décimo caso: expectativa sobre-ajustada, respuesta válida).
Operación: backups diarios 02:00 + réplica al host, restore probado (2771),
systemd con `Restart=always` (resurrección verificada con kill -9), migraciones
alembic hasta `0009_ia_observabilidad`.

Referencia técnica completa: `docs/integracion-llamacpp.md`.
