# S8 — Puesta en marcha

---
title: "S8 — Puesta en marcha"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
---

> **Como** equipo, **quiero** el backend corriendo en vivo y verificado contra .NET,
> **para** construir Django sobre algo real.

**Objetivo:** FastAPI live `:5002` + evidencia de convivencia con .NET `:5001` misma DB.

## Procedimiento

1. `docker compose -f docker-compose.dev.yml up -d` (postgres + .NET, si no están arriba).
2. `uvicorn app.main:app --port 5002` (1 worker) desde `backend-fastapi/` con `.env`.
3. `python scripts/smoke_live.py` — checks:
   - `GET /health` → `{"status":"ok","db":"up"}`.
   - Login Mattias → 200 + claims válidos.
   - `GET /api/jerarquia/arbol` → 3 padres / 4 grupos / 53 áreas.
   - `GET /api/atenciones` con token → 200, solo propias (Diego) o todo (Jefe).
   - WS `/ws?access_token=` → `status_changed` + `send_message` eco.
   - Comparativa: conteo `atenciones` y `areas` igual en `:5001` y `:5002`.
   - JWT cruzado: `GET :5001/api/jerarquia/arbol` con `Authorization: Bearer <token-python>` → 200.
4. Todo verde → evidencia (salida del script) pegada en el mensaje del commit.

## Reglas

- **RN-S8-01:** el smoke no escribe (solo login + lecturas + WS efímero); Diego termina Ausente.
- **RN-S8-02:** si algo falla, se registra como bug de su spec (S1–S7), no se parcha en S8.
- **RN-S8-03:** puertos fijos: 5433 postgres, 5001 .NET, 5002 FastAPI.

## Archivos (crear)

```
backend-fastapi/scripts/smoke_live.py  # stdlib + `websockets` pineado si hace falta
```

## Criterios de aceptación

- Smoke 100% verde contra servicios reales levantados.
- JWT Python aceptado por .NET (o justificado si .NET no está disponible).
- Sin filas TEST ni cambios de estado residuales.

## Definition of Done

1. [ ] smoke verde documentado
2. [ ] ruff limpio (si hay código nuevo)
3. [ ] Sin cambios fuera de `backend-fastapi/` (+ nada en `backend/`, `frontend/`, compose)

## Fuera de alcance

❌ Fixes de bugs (van a su spec) · ❌ Docker propio (S11) · ❌ Django (S9).
