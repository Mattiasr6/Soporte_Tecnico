# Fase 3 — Lens local con el propio modelo (titular de tesis)

## Problema

La revisión nativa depende de prompts del proveedor que no llegan
(#4808, 4 occurrences). La revisión local no necesita a nadie: el motor
es nuestro.

## Diseño

`backend-fastapi/app/services/review_lens.py`:

- 4 pasadas (`riesgo`, `resiliencia`, `legibilidad`, `confiabilidad`), cada
  una con system enfocado y el diff como contexto (máx 8000 chars).
- Cada lens vota `bloqueador / observacion / ok` en primera línea.
- `parse_verdict`: respuesta sin formato → `observacion` (ojos humanos),
  nunca ok silencioso.
- `corroborate`: `bloqueador` exige ≥2 lenses; un solo bloqueador se
  degrada a `observacion`.
- I/O aislado en `_llama_chat` (misma forma que `routers/ia.py`);
  `run_review(diff, caller=...)` acepta caller falso en tests (sin GPU).

## Verificación

```bash
cd backend-fastapi
DATABASE_URL='postgresql+psycopg://x:x@localhost:5433/soporte_test' \
  .venv/bin/python -m pytest tests/test_review_lens.py -q
```

Vivo (requiere llama-server): `run_review(diff_real)` con caller por
defecto y 2+ corroboraciones para bloquear.

## Done

7 tests verdes sin GPU; LSP limpio; pipeline 1→2→3→4 completo y medido.
