# S3 — Atenciones

---
title: "S3 — Atenciones"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: ["S1"]
---

> **Como** técnico/jefe, **quiero** CRUD de atenciones + batch + stats con las reglas actuales,
> **para** operar contra la misma DB.

**Objetivo:** paridad total del `AtencionesController` en snake_case, con identidad sustituible.

## Endpoints (`app/routers/atenciones.py`)

| Método | Path | Auth S3 | Lógica |
|--------|------|---------|--------|
| GET | `/api/atenciones?usuario_id=` | X-User-Id | Jefe/can_view → todo o filtro; resto solo propio. Incluye `usuario_nombre`, `grupo_padre_nombre`, `grupo_nombre`, `area_nombre`, `colaborador_nombre`. Orden: fecha desc, id desc |
| GET | `/api/atenciones/stats` | X-User-Id + rol | Solo Jefe/can_view (401 si no). Mismas 7 agregaciones + rango opcional |
| POST | `/api/atenciones/batch` | X-User-Id | `{atenciones: [...]}` → `{registros_insertados}` |
| PUT | `/api/atenciones/{id}` | X-User-Id | Propio o Jefe; sincroniza legacy; 204 |
| DELETE | `/api/atenciones/{id}` | X-User-Id | Propio o Jefe; físico; 204 |

## Reglas

- **RN-S3-01:** identidad = `require_user` (header temporal); S5 la reemplaza por JWT, rutas intactas.
- **RN-S3-02:** batch vacío → 400; categoría inválida → 400 con lista de las 8; FK inexistente → 400.
- **RN-S3-03:** resolución `area_id` > `grupo_id` > `grupo_padre_id` > legacy string;
  si hay FK se deriva `area_solicitante` del nombre real; si solo legacy, se intenta mapear a FKs por nombre.
- **RN-S3-04:** `fuera_de_turno` se calcula en servidor al crear (nunca input).
- **RN-S3-05:** `por_area` agrupa por legacy `area_solicitante`, no por FK (paridad).

## Catálogo de errores

| Código | Condición | HTTP |
|--------|-----------|------|
| ERR-S3-01 | sin X-User-Id / user inexistente | 401 |
| ERR-S3-02 | rol insuficiente (stats, ajeno) | 401 stats como .NET, 403 PUT/DELETE |
| ERR-S3-03 | atención inexistente | 404 |
| ERR-S3-04 | batch inválido | 400 + mensaje |
| ERR-S3-05 | body malformado | 422 estándar |

## Archivos (crear)

```
backend-fastapi/app/core/security.py     # require_user (header temporal) + roles
backend-fastapi/app/services/horarios.py # EstaFueraDeHorario + parse bloques + America/La_Paz
backend-fastapi/app/schemas/atencion.py  # Create, Update, Out, BatchIn/Out, StatsOut
backend-fastapi/app/routers/atenciones.py
backend-fastapi/tests/test_atenciones.py # roles, batch, validaciones, stats, PUT/DELETE
```

## Criterios de aceptación

- Técnico ve solo las suyas; Jefe ve todo y filtra por `usuario_id`.
- Batch mixto (FK + legacy) resuelve bien; categoría mala → 400; lista vacía → 400.
- Stats cuadran con .NET contra la misma DB (mismo total y desgloses).
- PUT con `area_id` actualiza `area_solicitante` al nombre real.
- DELETE ajeno como técnico → 403; como Jefe → 204.

## Definition of Done

1. [ ] 5 endpoints verificados contra `postgres-dev` real (sin ensuciar datos reales)
2. [ ] tests verdes · ruff + basedpyright limpios
3. [ ] Sin cambios fuera de `backend-fastapi/`

## Fuera de alcance

❌ JWT real (S5) · ❌ import CSV (S4) · ❌ UI.
