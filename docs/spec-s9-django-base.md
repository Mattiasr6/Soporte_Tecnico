# S9 — Django base + atenciones

---
title: "S9 — Django base + atenciones"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
---

> **Como** técnico, **quiero** login + lista/registro de atenciones en Django con la gramática starbucks,
> **para** operar sin Next.js.

**Objetivo:** frontend Django funcional (sin ORM) contra FastAPI live.

## Arquitectura

```
[Browser] --HTTP--> [Django :8000 views] --HTTP Bearer--> [FastAPI :5002] --> [postgres-dev]
```

Django: sin modelos/migraciones. JWT en sesión firmada (cookies, `SESSION_ENGINE=signed_cookies`, sin DB).
WS directo browser→FastAPI (JS plano, no pasa por Django).

## Pantallas S9

| Ruta Django | Consume | Template |
|-------------|---------|----------|
| `/login/` | `POST /api/auth/login` | form email/password → guarda JWT en sesión |
| `/atenciones/` | `GET /api/atenciones` + `arbol` | tabla + filtros |
| `/atenciones/nueva/` | `POST /api/atenciones/batch` (1 item) + `arbol` | form + selector Padre→Grupo→Área |
| `/atenciones/<id>/` | GET + PUT | detalle + edición |

Flujo diseño por pantalla: Excalidraw → mockup OpenDesign (starbucks) → template. Mockups fuera de git.

## Reglas

- **RN-S9-01:** sin login válido → redirect `/login/` (decorador propio).
- **RN-S9-02:** el JWT nunca sale del servidor salvo en `Authorization` hacia FastAPI;
  sesión cifrada por `SECRET_KEY` (env).
- **RN-S9-03:** errores FastAPI (400/401/403/404) → mensajes en template, no 500.
- **RN-S9-04:** token expirado/inválido → limpia sesión + redirect login con aviso.
- **RN-S9-05:** CSS con tokens starbucks en `static/`.

## Archivos (crear)

```
frontend-django/manage.py + config/settings.py + config/urls.py
frontend-django/atenciones/views.py + urls.py + forms.py
frontend-django/templates/{base,login,lista,nueva,detalle}.html
frontend-django/static/css/tokens.css + app.css
frontend-django/requirements.txt (Django + requests, pineado)
frontend-django/tests/test_views.py (FastAPI mockeado) + smoke Django→FastAPI live
```

## Criterios de aceptación

- Login real → lista con datos live; técnico ve solo suyas, jefe todo.
- Registro con selector funcional crea atención visible en ambas APIs.
- Detalle edita y sincroniza `area_solicitante`.
- Sesión sin JWT → redirect; token malo → aviso + login.

## Definition of Done

1. [ ] 4 pantallas contra FastAPI live real
2. [ ] tests verdes · ruff limpio
3. [ ] Sin modelos/migraciones en Django (cero `models.py`)
4. [ ] Sin cambios fuera de `frontend-django/`

## Fuera de alcance

❌ Dashboard/resto (S10) · ❌ ORM · ❌ WS en templates.
