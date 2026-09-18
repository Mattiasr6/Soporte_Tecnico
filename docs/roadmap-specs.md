# Roadmap de specs — Migración Python (FastAPI + Django templates)

Rama: `python-experiment` · DB: misma `postgres-dev` (`:5433`) · Convivencia .NET/Next hasta S10.

| Spec | Título | Estado |
|------|--------|--------|
| S1 | Base + DB: FastAPI, modelos espejo, alembic, seed bcrypt | aprobada y redactada (`docs/spec-s1-base-db.md`) |
| S2 | Jerarquía: grupos-padres, grupos, áreas, árbol | aprobada y redactada (`docs/spec-s2-jerarquia.md`) |
| S3 | Atenciones: GET/roles, stats, PUT, DELETE, batch | aprobada y redactada (`docs/spec-s3-atenciones.md`) |
| S4 | Import CSV | aprobada y redactada (`docs/spec-s4-csv.md`) |
| S5 | Auth mínima: login JWT compatible + guards | aprobada y redactada (`docs/spec-s5-auth.md`) |
| S6 | Resto v2: horarios, usuarios, announcements | pendiente |
| S7 | Realtime: paridad SignalR WS | pendiente (al final) |
| S8 | Django templates: base + atenciones (wireframe→mockup→template) | pendiente |
| S9 | Django templates: dashboard + resto pantallas | pendiente |
| S10 | Cutover: paridad, pruebas directas, apagado .NET/Next | pendiente |

Decisiones globales: Python 3.13 · pip+venv+requirements · SQLAlchemy sync+psycopg · alembic aditivo ·
`backend-fastapi/` · dev host uvicorn `:5002` · starbucks como referencia visual · IA = tooling, sin features IA ·
todo el ecosistema Python en snake_case.
