# S7 — Realtime WS

---
title: "S7 — Realtime WS"
status: "approved"
version: "1.0"
priority: "media"
dependencies: ["S1", "S5", "S6"]
---

> **Como** cliente conectado, **quiero** estados, chat y anuncios en vivo por WS nativo,
> **para** la misma experiencia del hub.

**Objetivo:** paridad funcional de `AppHub` sobre WebSocket nativo + broadcasts desde REST.

## Protocolo (`/ws?access_token=<JWT>`)

| Dirección | Mensaje | Contenido |
|-----------|---------|-----------|
| S→C | `status_changed` | `{usuario_id, nombre, estado, motivo, colaborador_nombre, timestamp}` |
| S→C | `receive_message` | `{nombre, role, message, timestamp}` |
| S→C | `receive_announcement` | `{message}` |
| C→S | `send_message` | `{message}` |
| Cierre | `4401` | sin token / inválido / user inexistente |

Cada mensaje WS es JSON `{type, ...payload}`. `timestamp` = `HH:mm` UTC (paridad).

## Reglas

- **RN-S7-01:** connect válido: si `estado_actual` es Ausente → Disponible (+`updated_at`),
  broadcast `status_changed` (motivo/colaborador null).
- **RN-S7-02:** disconnect: solo si es la **última** conexión del usuario y está Disponible
  → Ausente + broadcast `ausente`.
- **RN-S7-03:** PATCH estado y POST announcements emiten broadcast (adiós `TODO(S7)`).
- **RN-S7-04:** registry `{conn_id: user_id}` en memoria; dev con 1 worker (documentado).
- **RN-S7-05:** announcements sigue en memoria S6; el WS solo difunde.

## Catálogo de errores

| Código | Condición | Efecto |
|--------|-----------|--------|
| ERR-S7-01 | sin access_token / inválido / expirado / user inexistente | cierre 4401 |
| ERR-S7-02 | JSON malformado del cliente | se ignora (log warn), conexión sigue |

## Archivos (crear)

```
backend-fastapi/app/realtime/hub.py   # registry, connect/disconnect, broadcast()
backend-fastapi/app/realtime/ws.py    # endpoint /ws + loop send_message
backend-fastapi/app/routers/*.py      # PATCH estado y POST announcements emiten (modifican)
backend-fastapi/tests/test_realtime.py
```

## Criterios de aceptación

- Connect como Diego (Ausente) → recibe `status_changed` disponible; DB queda Disponible.
- 2 conexiones, cierra 1 → sin broadcast; cierre última → `ausente` (verificado en DB + observador).
- `send_message` desde A lo recibe B.
- PATCH estado y POST announcement llegan al WS suscrito.
- Sin token → 4401.

## Definition of Done

1. [ ] verificado contra `postgres-dev` real, estados restaurados a Ausente
2. [ ] tests verdes · ruff + basedpyright limpios
3. [ ] Sin cambios fuera de `backend-fastapi/`

## Fuera de alcance

❌ Protocolo SignalR · ❌ pubsub multi-worker · ❌ historial de chat servidor.
