# S2 — Jerarquía

---
title: "S2 — Jerarquía"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: ["S1"]
---

> **Como** frontend, **quiero** los endpoints de jerarquía con forma estable,
> **para** armar el selector Padre→Grupo→Área.

**Objetivo:** paridad de lectura de jerarquía contra la misma DB, en snake_case.

## Convención global Python (aplica a S1–S10)

Todo el ecosistema Python en **snake_case**: attrs, requests y responses.
Sin aliases camelCase. El consumidor objetivo son templates Django;
Next.js sigue contra .NET hasta el cutover (S10).

## Endpoints (router `app/routers/jerarquia.py` + `areas.py`)

| Método | Path | Query | Respuesta |
|--------|------|-------|-----------|
| GET | `/api/jerarquia/grupos-padres` | — | `[{id, nombre, descripcion, orden}]` por `orden` |
| GET | `/api/jerarquia/grupos` | `grupo_padre_id?` | `[{id, grupo_padre_id, nombre, activo}]` por `nombre` |
| GET | `/api/jerarquia/areas` | `grupo_padre_id?`, `grupo_id?` | `[{id, grupo_padre_id, grupo_id, nombre, activo}]`, solo activas, por `nombre` |
| GET | `/api/jerarquia/arbol` | — | `{padres, grupos, areas}` plano, mismos órdenes |
| GET | `/api/areas` | — | `string[]` legacy (ver RN-S2-02) |

## Reglas

- **RN-S2-01:** `/arbol` no arma árbol; devuelve las 3 listas planas. El cliente compone.
- **RN-S2-02:** `GET /areas` réplica exacta: distinct no-vacío de `Atenciones.AreaSolicitante`
  + 8 fijas + `Aula A-01..A-12`, `B-01..B-21`, `C-01..C-20`, `D-01..D-18`, `E-01..E-05`,
  ordenado; si el total queda en 1 elemento, devolver el fallback de 33 nombres.
- **RN-S2-03:** filtros opcionales y combinables; sin params = todo.
- **RN-S2-04:** sin auth en S2; S5 añade el guard sin tocar lógica.

## Catálogo de errores

| Código | Condición | HTTP | Mensaje |
|--------|-----------|------|---------|
| ERR-S2-01 | query int inválido | 422 | detalle FastAPI estándar |
| — | sin datos | 200 | `[]` (nunca 404 en listados) |

## Archivos (crear)

```
backend-fastapi/app/schemas/jerarquia.py   # GrupoPadreOut, GrupoOut, AreaOut (snake_case directo)
backend-fastapi/app/routers/jerarquia.py   # 4 endpoints
backend-fastapi/app/routers/areas.py       # GET /areas legacy
backend-fastapi/tests/test_jerarquia.py    # conteos, orden, forma, filtros, fallback areas
# main.py: solo montar routers (1 línea por router)
```

## Criterios de aceptación

- `arbol`: 3 padres en orden (Administrativos, Académicos, Extras);
  grupos y áreas alfabéticas; áreas todas activas.
- `grupos?grupo_padre_id=1` ⊆ `grupos` sin filtro; `areas?grupo_id=X` solo de ese grupo.
- `GET /areas` incluye `Aula B-02` y `Plaza UPDS` (vía extras/distinct).
- Conteos iguales a los de .NET contra la misma DB.

## Definition of Done

1. [ ] 5 endpoints verificados contra `postgres-dev` real
2. [ ] tests verdes (fallback legacy sin tocar datos reales)
3. [ ] ruff + basedpyright limpios
4. [ ] Sin cambios fuera de `backend-fastapi/`

## Fuera de alcance

❌ Auth/guards (S5) · ❌ escritura (S3) · ❌ UI.
