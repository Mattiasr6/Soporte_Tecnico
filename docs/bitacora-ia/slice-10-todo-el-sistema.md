# Slice 10 — Todo el sistema como conocimiento

## Objetivo

Responder con usuarios, áreas y estadísticas exactas, no solo tickets.

## Prompts

> `y hay manera de que todos los datos que ya tiene el sistema, el LLM pueda usarlos para mejorar sus habilidades?`

## Respuesta / acciones del agente

1. Indexado extendido: Usuarios activos (nombre/rol/especialidad), Áreas (con grupo), ficha de ticket enriquecida (descripción+solución+categoría+área+medio+observaciones+registrante).
2. Intent SQL determinista `_ESTADISTICAS` y `_estadisticas_tecnico` con matching por tokens normalizados (sin tildes).
3. Híbrido vectorial + BM25 con RRF (`rank-bm25`).
4. Medición anti-intuitiva: el reranker cross-encoder **empeoraba** (KB exacta 6ta de 12) → OFF por defecto (`RERANK=1`), documentado como hallazgo.
5. Verificado: 2845 docs; técnico/área/stats responden exacto.

## Evidencia

- Commits `286f7d5`, `5bfbc7a`; `requirements.txt` (+`rank-bm25==0.2.2`)
- Ejemplos: técnico 519/56, área→grupo, medio Interno 1468 vs E-ticket 4

## Decisión / hallazgo

- Medir antes de asumir: el reranker "mejor" perdía contra L2 calibrado en este dominio.
