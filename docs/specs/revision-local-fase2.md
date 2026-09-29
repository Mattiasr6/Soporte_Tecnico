---
title: "Fase 2 — Revisión por rebanadas con presupuesto fijo"
status: "draft"
version: "1.0"
dependencies: ["backend-fastapi", "pytest en backend-fastapi/.venv", "revision-local-fase1.md"]
---

### Problema

Un candidato con muchas rutas o una ruta muy grande supera el presupuesto de
contexto de las lentes (`lens_context_budget_exceeded`) y la revisión local
falla entera. Además, al revisar un candidato en partes no había una regla
explícita para combinar los veredictos parciales: cualquiera podía "bajar" el
resultado final.

### Diseño — `slice_candidate(items, budget_lines=400)`

- `items`: lista de `(ruta, líneas)` en el orden original. Greedy: se acumulan
  rutas mientras la suma no supere `budget_lines`; al desbordar, se cierra la
  rebanada actual y se abre otra.
- Cada rebanada: `{"paths": [...], "total_lines": int, "over_budget": bool}`.
- Toda ruta aparece exactamente una vez, en el orden de entrada.
- Una ruta sola mayor al presupuesto (ej. 900 líneas con presupuesto 400)
  queda en su propia rebanada con `over_budget: True`: **no se recorta** el
  archivo; se señala para que el llamador decida (revisarla sola o saltearla).
  Una rebanada de varias rutas nunca supera el presupuesto.
- `DEFAULT_BUDGET_LINES = 400`. Sin I/O, solo stdlib, funciones puras.

### Diseño — `merge_verdicts(verdicts)`

Vocabulario `ok` < `observacion` < `bloqueador` (`VERDICT_RANK`); gana el peor.
Lista vacía → `ok`. Un valor desconocido lanza `ValueError`: nunca se degrada
en silencio un veredicto no reconocido.

### Verificación

```bash
cd backend-fastapi
DATABASE_URL='postgresql+psycopg://x:x@localhost:5433/soporte_test' \
  .venv/bin/python -m pytest tests/test_review_slices.py -q
```

El `DATABASE_URL` ficticio solo satisface la guarda de `tests/conftest.py`; la
suite no abre conexión. Esperado: `5 passed`.

### Criterios de done

- [ ] 61 rutas de docs (5–60 líneas) con presupuesto 400: toda rebanada
      `total_lines <= 400`, las 61 rutas cubiertas una vez y en orden.
- [ ] Ruta única de 900 líneas → una rebanada con `over_budget: True`.
- [ ] Lista vacía → `[]` rebanadas; `merge_verdicts([]) == "ok"`.
- [ ] `["ok","observacion","ok"] → "observacion"`; `["ok","bloqueador",
      "observacion"] → "bloqueador"`; veredicto desconocido → `ValueError`.
- [ ] `review_slices.py` es puro: solo stdlib (`typing`), sin I/O.

Fuera de alcance: ponderar por tier (fase 1 solo clasifica; el presupuesto es
por líneas), paralelizar la revisión de rebanadas y persistir veredictos.
