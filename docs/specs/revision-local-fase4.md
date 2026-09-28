# Fase 4 — La revisión aprende de sus falsos positivos

## Problema

El proveedor marcó `high` tres candidatos de docs por el nombre de un PDF
(`spec-s5-auth.pdf`). Sin memoria, ese error se repite el 100% de las veces.

## Diseño

`backend-fastapi/app/services/review_feedback.py` (puro, stdlib):

| Función | Qué hace |
|---|---|
| `record_disagreement(provider, local, human, signal)` | Registra la terna de veredictos; falso positivo = proveedor por encima del humano |
| `suggest_tuning(log, min_repeat=2)` | Con ≥2 falsos positivos de la misma señal, sugiere regla `allowlist "<señal>"` |

Reglas: un solo desacuerdo es dato, no regla. Proveedor por debajo del
humano nunca es falso positivo (dirección fail-closed intacta). Tier
desconocido → `ValueError`, nunca degradación silenciosa.

## Verificación

```bash
cd backend-fastapi
DATABASE_URL='postgresql+psycopg://x:x@localhost:5433/soporte_test' \
  .venv/bin/python -m pytest tests/test_review_feedback.py -q
```

## Done

6 tests verdes; el caso real (`auth in filename` ×3) produce la sugerencia
de allowlist; `suggest_tuning` vacío ante un solo dato.
