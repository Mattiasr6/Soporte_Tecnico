---
title: "Fase 1 — Riesgo medido en la revisión local (clasificador por rutas)"
status: "draft"
version: "1.0"
dependencies: ["backend-fastapi", "pytest en backend-fastapi/.venv"]
---

### Problema y objetivo

La clasificación del candidato era heurística: una ruta larga o una palabra del
nombre elevaba el riesgo (un PDF en `docs/pdf/docs/` se trataba como código; un
binario podía quedar sin decisión explícita). Ahora el tier se decide con
reglas deterministas, sin I/O ni dependencias externas, y *fail closed*: lo
desconocido se trata como código ejecutable.

### Diseño — `classify_path(path)`

Orden de evaluación; el primero que coincide gana:

| # | Condición sobre la ruta | Tier |
|---|-------------------------|------|
| 1 | basename `.env*`, `*secret*`, `*credential*`, `*private*key*`, `*.pem`, `*.key`; o la ruta termina en `.pem` / `.key` | `critico` |
| 2 | extensión de código (`.py .js .ts .tsx .jsx .sh .sql .html .vue`), segmento `alembic` / `migrations`, `Dockerfile*`, `docker-compose*` | `activo` |
| 3 | extensión binaria (`.pdf .png .jpg .jpeg .gif .webp .ico .woff .woff2 .ttf .mp4 .zip .vmdk`) | `opaco` |
| 4 | documentación (`.md .rst .txt`) | `pasivo` |
| 5 | cualquier otra extensión, o sin extensión | `activo` (*fail closed*) |

### Diseño — `classify_candidate(paths)`

Devuelve `{tier, por_path, motivo}` y aplica esta escalada:

1. algún `critico` → `critico` (`motivo`: `critical path: <ruta>`).
2. si no, algún `activo` → `activo` (`motivo`: `N active paths (max tier)`).
3. si no, hay documentación legible → `pasivo` (`all paths passive docs`):
   un adjunto binario dentro de un bundle de docs no escala el tier.
4. si no, solo binarios → `opaco`.
5. lista vacía → `pasivo` con motivo que menciona `empty`.

`TIER_RANK` expone el orden de severidad (`pasivo` 0 → `critico` 3).

### Verificación

```bash
cd backend-fastapi
DATABASE_URL='postgresql+psycopg://x:x@localhost:5433/soporte_test' \
  .venv/bin/python -m pytest tests/test_review_risk.py -q
```

El `DATABASE_URL` ficticio solo satisface la guarda de `tests/conftest.py`; la suite no abre conexión. Esperado: `6 passed`.

### Criterios de done

- [ ] 6 tests en verde: 61 rutas (`.md` + `.pdf`) → `pasivo`; PDF `spec-s5-auth.pdf`
      → `opaco` sin escalar por nombre; un `.py` entre docs → `activo`; `.env` →
      `critico`; `.xyz` → `activo`; lista vacía → `pasivo`.
- [ ] `review_risk.py` es puro: solo stdlib (`os`, `re`), sin I/O.

Fuera de alcance: selección automática de lentes por tier en el pipeline, y análisis de contenido (el clasificador mira la ruta, no los bytes).
