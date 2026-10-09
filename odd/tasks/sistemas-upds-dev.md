# Sistemas UPDS: frontend-horarios servido por FastAPI (sin Supabase)

## Objetivo
`frontend-horarios` (ex ASIGNACION_DE-HORARIOS, Angular 22) deja de depender de
Supabase y funciona contra el backend FastAPI + Postgres de Soporte_Tecnico.
Meta final: un solo backend para ambos sistemas y eliminar Supabase.

## Problema / por qué
El frontend consulta tablas directo con supabase-js (90 `.from()`, 9 `.rpc()`,
44 usos de auth, 8 de storage en 21 archivos). La lógica vive en Postgres
(5278 líneas SQL en `frontend-horarios/supabase/`): triggers anti-choque,
~20 RPC, ~58 políticas RLS sobre `auth.uid()` (51 refs). FastAPI no entiende nada de eso.

## Decisiones
- Opción 1 (migración real), no puente PostgREST. Elegida por el usuario 2026-10-08.
- Esquema propio `horarios` en la misma base (sin chocar con las tablas PascalCase de Soporte).
- Triggers/funciones Postgres puros se conservan; RLS sale y los permisos pasan a FastAPI.
- `auth.uid()` se reemplaza por contexto de sesión que fija FastAPI (`SET LOCAL`).
- `perfiles` se vincula a `"Usuarios"."Id"`. La identidad de auxiliares (usuarios reales)
  la resuelve OTRO agente en otra rama: no tocar; integrar cuando llegue.
- Storage Supabase → archivos en disco como ya hace Soporte (`data/`).
- Datos de Supabase prod: fuera de alcance por ahora (solo dev).

## Alcance / restricciones
- Rama `feat/sistemas-upds-dev`, worktree `stupds/Soporte_Tecnico2`.
- Entorno aislado `soporte-upds` (pg 5435 `soporte_upds`, api 5013, web 8013).
  Prod (5002/8001/5433) y dev (5012/8011/5434) NO se tocan.
- Repo público: escanear secretos antes de cada commit.
- Estrategia de entrega: `ask-on-risk` (pronóstico > 400 líneas → preguntar al cortar PRs).

## Tareas
- [x] T1 Esquema `horarios`: migración Alembic 0021 que porta el SQL de Supabase
      (sin auth/storage/RLS), `perfiles` ↔ `Usuarios`, reemplazo de `auth.uid()`.
      Check: `alembic upgrade head` en soporte-upds + tests de triggers anti-choque.
- [ ] T2 API base: CORS para Angular dev, dependencia de sesión con contexto de usuario,
      mapeo de roles, `GET /api/horarios/me`.
- [ ] T3 Auth en Angular: login contra `/api/auth/login`, interceptor JWT, proxy dev a 5013.
- [ ] T4 Catálogos (ambientes, ambiente_pcs, materias, carreras, docentes, feriados, bloques…).
- [ ] T5 Asignaciones, cesiones, reservas, reubicaciones + RPC de choques/ocupación.
- [ ] T6 Operación: turnos, reportes de turno, atenciones, fallas, bajas, objetos perdidos, fotos.
- [ ] T7 Dashboards (`fn_dashboard_*`).
- [ ] T8 Quitar `@supabase/supabase-js` y `environment.supabase*`.

## Progreso
- 0ce5310 entorno aislado soporte-upds (migrado 0020 + seed).
- d0e6f5a import de ASIGNACION_DE-HORARIOS@0fc5a44 en `frontend-horarios/`.

- T1 (delegado, writer): migración `0021_horarios_schema` + `alembic/sql/0021_horarios/*.sql`
  (generado vía pg_dump del SQL de Supabase 01-33 sin 00/05, RLS/auth/storage fuera,
  `auth.uid()` → `horarios.fn_usuario_actual()` desde `app.usuario_id`). Evidencia:
  RED 7/8 fallan sin migración; upgrade/downgrade/upgrade OK en `soporte_upds_test`;
  `pytest tests/test_horarios_schema.py tests/test_health.py` 9 passed; `soporte_upds` en head.
  Pendiente para la API: reglas que vivían solo en RLS (`99_rls_reference.sql`).

## Siguiente paso
T2 API base.
