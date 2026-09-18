# S6 — Resto v2

---
title: "S6 — Resto v2"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: ["S1", "S5"]
---

> **Como** técnico/jefe, **quiero** horarios, usuarios y announcements con las reglas actuales,
> **para** completar la paridad REST.

**Objetivo:** paridad de los 3 controladores restantes, sin realtime (S7).

## Endpoints

| Método | Path | Auth | Lógica |
|--------|------|------|--------|
| GET | `/api/horarios?mes=&anio=` | JWT | Jefe todo; resto propio. Incluye `nombre` técnico. Orden por nombre |
| POST | `/api/horarios` | JWT Jefe/can_view | Upsert por (usuario,mes,anio); target Tecnico existente o 400; 204 |
| DELETE | `/api/horarios/{id}` | JWT Jefe/can_view | 404 si no existe; 204 |
| GET | `/api/horarios/cobertura?mes=&anio=` | JWT | 4 franjas con técnicos (comparación string); default mes/año actual |
| GET | `/api/usuarios` | JWT | Solo Tecnico/Jefe + `estado_actual` efectivo |
| GET | `/api/usuarios/me` | JWT | Propio + efectivo; 404 si no registrado |
| PATCH | `/api/usuarios/{id}/especialidad` | JWT Jefe/can_view | 404 si no existe; 204 |
| GET/PUT | `/api/usuarios/notas` | JWT | Propias (`{contenido}`) |
| PATCH | `/api/usuarios/estado` | JWT | disponible/ocupado; 400 ausente-manual/inválido; 204, sin broadcast |
| GET | `/api/announcements` | anónimo | `{message}` (null si vacío) |
| POST | `/api/announcements` | JWT Jefe/can_view | Guarda (vacío→null), 200 con `{message}`, sin broadcast |

## Reglas

- **RN-S6-01:** `estado_efectivo`: Ausente→`ausente`, Extraturno→`extraturno`,
  Disponible/Ocupado fuera de horario→`extraturno`, si no minúsculas del guardado.
- **RN-S6-02:** broadcasts `StatusChanged`/`ReceiveAnnouncement` pendientes a S7 (`# TODO(S7)`).
- **RN-S6-03:** cobertura usa comparación lexicográfica de strings `HH:MM` (paridad).
- **RN-S6-04:** `me` y notas operan sobre el usuario del token.

## Catálogo de errores

| Código | Condición | HTTP |
|--------|-----------|------|
| ERR-S6-01 | asignar a no-Tecnico/inexistente | 400 "Tecnico no encontrado" |
| ERR-S6-02 | horario a borrar inexistente / usuario inexistente | 404 |
| ERR-S6-03 | estado inválido o ausente manual | 400 |
| ERR-S6-04 | sin rol para asignar/borrar/especialidad/announce | 403 |

## Archivos (crear)

```
backend-fastapi/app/schemas/horario.py      # HorarioOut, AsignarIn, CoberturaOut
backend-fastapi/app/schemas/usuario.py      # UsuarioOut, EspecialidadIn, NotasIn, EstadoIn
backend-fastapi/app/schemas/announcement.py # AnnouncementOut
backend-fastapi/app/routers/horarios.py
backend-fastapi/app/routers/usuarios.py
backend-fastapi/app/routers/announcements.py
backend-fastapi/app/services/estados.py     # estado_efectivo (puro)
backend-fastapi/tests/test_resto_v2.py
```

## Criterios de aceptación

- Cobertura cuadra con .NET para el mes actual (mismas franjas y técnicos).
- `me` devuelve efectivo correcto según horario real del mes.
- PATCH estado a `ausente` → 400; a `DISPONIBLE` → 204.
- Announcements: GET sin token 200; POST técnico → 403; POST jefe vacío → `{message: null}`.
- Limpieza total: horarios 2099 borrados, estados restaurados, announcement restaurado.

## Definition of Done

1. [ ] 11 endpoints verificados contra `postgres-dev` real
2. [ ] tests verdes · ruff + basedpyright limpios
3. [ ] Sin cambios fuera de `backend-fastapi/`

## Fuera de alcance

❌ Broadcasts realtime (S7) · ❌ UI.
