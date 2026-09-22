# Roadmap de specs — Migración Python (FastAPI + Django templates)

Rama: `python-experiment` · DB: misma `postgres-dev` (`:5433`) · Convivencia .NET/Next hasta S10.

| Spec | Título | Estado |
|------|--------|--------|
| S1 | Base + DB: FastAPI, modelos espejo, alembic, seed bcrypt | aprobada y redactada (`docs/spec-s1-base-db.md`) |
| S2 | Jerarquía: grupos-padres, grupos, áreas, árbol | aprobada y redactada (`docs/spec-s2-jerarquia.md`) |
| S3 | Atenciones: GET/roles, stats, PUT, DELETE, batch | aprobada y redactada (`docs/spec-s3-atenciones.md`) |
| S4 | Import CSV | aprobada y redactada (`docs/spec-s4-csv.md`) |
| S5 | Auth mínima: login JWT compatible + guards | aprobada y redactada (`docs/spec-s5-auth.md`) |
| S6 | Resto v2: horarios, usuarios, announcements | aprobada y redactada (`docs/spec-s6-resto.md`) |
| S7 | Realtime: paridad SignalR WS | aprobada y redactada (`docs/spec-s7-realtime.md`) |
| S8 | Puesta en marcha: uvicorn live + smoke + convivencia .NET | aprobada y redactada (`docs/spec-s8-live.md`) |
| S9 | Django templates: base + atenciones (wireframe→mockup→template) | **completada** — 4 pantallas (login, lista, registrar con batch, modal ticket editar/eliminar), sidebar global con gating por rol, apartado auxiliares navegable |
| S10 | Django templates: dashboard + resto pantallas | **en curso** — ✅ dashboard, ✅ `/jerarquia` (admin del catálogo para jefes), ✅ selector de jerarquía en árbol, ✅ paginación de la lista; pendiente: reportes, horarios, perfil, launcher, bloc de notas (wireframe por pantalla antes de código) |
| S11 | Cutover: paridad final, apagado .NET/Next, compose definitivo | pendiente |
| S12 | Migración datos prod | **descartada por decisión del usuario**: v2 arranca de 0 desde septiembre (274 atenciones) y v1 queda como evidencia de trabajo. No se migra la historia |

## Diferidos (anotados por el usuario)

- **Apartado `/perfil` (para spec futura).** Cada usuario debe poder ver su **propio** perfil y jugar con sus
  estadísticas. Los **Jefes** entran a `/perfil` y pueden ver el suyo **y** el de los técnicos.
  Ahí se retrabajan los 3 gráficos de técnicos que hoy viven en el dashboard
  (scatter "carga vs fuera de turno", "rendimiento por técnico", "colaboraciones") más el radar,
  que se aplana cuando el filtro tiene una sola categoría dominante.
  Decidido el 2026-09-20: no tocarlos en el dashboard; salen del dashboard cuando exista `/perfil`.

- **Todo lo demás pendiente está en [`docs/pendientes-spec.md`](pendientes-spec.md)**, agrupado por
  spec futura (J1 bootstrap por código, J2 jerarquía v2, P1 perfil, N1 notas, H1 horarios, R1 reportes,
  L1 launcher, O1 operación/seguridad, D1 datos), con el contexto ya investigado para no re-descubrirlo.

Decisiones globales: Python 3.13 · pip+venv+requirements · SQLAlchemy sync+psycopg · alembic aditivo ·
`backend-fastapi/` · dev host uvicorn `:5002` · starbucks como referencia visual · IA = tooling, sin features IA ·
todo el ecosistema Python en snake_case.
