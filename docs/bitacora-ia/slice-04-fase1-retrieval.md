# Slice 04 — Fase 1 retrieval (`/ia/*` + Chroma)

## Objetivo

Búsqueda semántica sobre atenciones con alucinación = 0 (mostrar tickets reales, sin generar texto).

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `(Decisiones previas: datos reales, burbuja en Django, nombre Wilmercito).`
> `Flujo de trabajo del agente: explorar backend-fastapi/app (routers, Atencion). Crear app/services/ia_retrieval.py + app/routers/ia.py. Registrar router en main.py.`

## Respuesta / acciones del agente

1. Impacto GitNexus previo (`app` no resuelto → riesgo LOW por inspección: solo agrega import + `include_router`).
2. Creados: `ia_retrieval.py` (lazy embeddings multilingües, Chroma persistente, `.tolist()` obligatorio, indexado idempotente `atencion_<Id>`) y `ia.py` (`/buscar`, `/reindexar`, `/estado`, umbral 0.35 heredado).
3. Sincronizado a VM, indexado **2771/2771**.
4. Calibración real que rompió el umbral heredado: distancias L2 al cuadrado (1.2–11.6), no coseno.
   Fix: `normalize_embeddings=True` → coseno 0..2; medido buenos 0.06–0.42, mundial 0.61 → **umbral 0.5**.
5. Wipe + reindex limpio; `/ia/buscar` devuelve 3 tickets reales (ej: impresora → 0.238).

## Evidencia

- Commits: `9dff9fb` (docs/contratos), `8bd7be5` (fix django)
- `POST /api/ia/reindexar` → `{'nuevas': 2771, 'total': 2771}`
- Medición de distancias por query (impresora/internet/mundial/toner/cuentas)

## Decisión / hallazgo

- Los umbrales no se heredan entre embeddings: se calibran con datos propios.
- Chroma `query` sin normalizar devuelve L2²; normalizado equivale a coseno.
