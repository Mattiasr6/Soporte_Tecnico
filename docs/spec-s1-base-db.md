# S1 — Base + DB FastAPI

---
title: "S1 — Base + DB FastAPI"
status: "approved"
version: "1.0"
priority: "alta"
dependencies: []
---

> **Como** equipo, **quiero** FastAPI conectado a `postgres-dev` con modelos espejo,
> **para** construir los endpoints encima.

**Objetivo:** base ejecutable con paridad de esquema y seed usable, sin tocar nada de .NET.

## Stack

| Capa | Tecnología | Versión | Notas |
|------|-----------|---------|-------|
| Backend | FastAPI | ≥0.115 | sync, sin async |
| DB driver | psycopg (v3) | ≥3.1 | sync |
| ORM | SQLAlchemy 2 | ≥2.0 | `Mapped`/`mapped_column`, espejo EF |
| Migraciones | Alembic | ≥1.13 | solo aditivas |
| Hash | passlib bcrypt | — | mismo formato `$2b$` |
| Tests | pytest + httpx | — | health + seed |
| Lint/tipos | ruff + basedpyright | — | limpios como DoD |
| Python | 3.13 | dev host venv; 3.13-slim en Docker (S10) | local del dev puede ser 3.14, CI fija 3.13 |

## Mapa de archivos (crear, nada existente se modifica)

```
backend-fastapi/app/main.py            # app + healthcheck GET /health
backend-fastapi/app/core/config.py     # env: DATABASE_URL, JWT_SECRET
backend-fastapi/app/db/base.py         # Base + engine sync + SessionLocal
backend-fastapi/app/db/session.py      # get_db dependency
backend-fastapi/app/models/*.py        # usuario, atencion, horario, grupo_padre, grupo, area (6)
backend-fastapi/app/schemas/*.py       # Pydantic mínimas (seed/tests)
backend-fastapi/scripts/seed.py        # upsert 9 usuarios + 3 padres (bcrypt conocida)
backend-fastapi/alembic/*              # env + revisión baseline espejo (sin aplicar cambios)
backend-fastapi/requirements.txt       # pineado
backend-fastapi/.env.example           # DATABASE_URL, JWT_SECRET (sin valores reales)
backend-fastapi/tests/test_health.py + test_seed.py
```

`.env` real no versionado.

## Contratos de datos (espejo exacto de EF)

Tablas: `Usuarios`, `Atenciones`, `Horarios`, `GruposPadres`, `Grupos`, `Areas`.
Mismos nombres de tabla/columna, tipos (int PK, varchar con límites EF,
`EstadoActual` como string, `FechaRegistro` date, defaults `Tecnico`/`Ausente`/false),
únicos (`Usuarios.Email`, `[GrupoPadreId,Nombre]`, `[GrupoPadreId,GrupoId,Nombre]`,
`[UsuarioId,Mes,Anio]`), FKs con mismos `ON DELETE` (Restrict/SetNull).

Seed: 9 usuarios (mismos Id/Email/DisplayName/Role/CanViewDashboard) + 3 padres
(1 Administrativos, 2 Académicos, 3 Extras); password = bcrypt de clave conocida.
Afecta DB compartida (también cambia su login en .NET) — asumido y aprobado.

## Flujos

1. Setup: `python3.13 -m venv .venv && pip install -r requirements.txt`, copiar `.env.example` → `.env`.
2. `uvicorn app.main:app --port 5002` → `GET /health` = `{"status":"ok","db":"up"}` (conexión real).
3. `python scripts/seed.py` → upsert idempotente (re-ejecutable, no duplica).
4. `alembic upgrade head` → no-op verificado (esquema ya existe por EF).

## Catálogo de errores

| Código | Condición | HTTP | Mensaje |
|--------|-----------|------|---------|
| ERR-S1-01 | DB inalcanzable | 503 | "Base de datos no disponible" |
| ERR-S1-02 | env requerido ausente | 500 arranque | "Falta DATABASE_URL/JWT_SECRET" (falla al arrancar) |
| ERR-S1-03 | seed con FK huérfana | 500 | "Seed inconsistente: <detalle>" |

## Reglas de negocio

- **RN-S1-01:** ningún DDL destructivo; `alembic autogenerate` se revisa a mano antes de aplicar.
- **RN-S1-02:** seed nunca borra; solo upsert por PK.
- **RN-S1-03:** secreto JWT jamás en código ni en git.

## Criterios de aceptación

- `GET /health` 200 con DB up, 503 con DB caída.
- Seed 2× seguidas → mismos 9 usuarios + 3 padres, sin duplicados.
- `pytest` verde; `ruff` + `basedpyright` limpios.
- .NET sigue arrancando y operando igual (convivencia intacta).

## Definition of Done

1. [ ] health + seed + mig no-op verificados contra `postgres-dev` real
2. [ ] tests verdes
3. [ ] ruff + basedpyright limpios
4. [ ] `.env` fuera de git, `.env.example` committed
5. [ ] Sin cambios en `backend/`, `frontend/`, migraciones EF

## Fuera de alcance

❌ Endpoints de negocio (S2–S6) · ❌ login/JWT (S5) · ❌ mail/codes · ❌ realtime (S7) ·
❌ Docker (S10) · ❌ UI.
