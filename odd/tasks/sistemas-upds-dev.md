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

- Prefijo de API del módulo: `/api/asignacion` (NO `/api/horarios`, que ya sirve los
  horarios de técnicos).
- Mapeo de roles (fuente única = `Usuarios.Role`, se re-sincroniza en cada request):
  Jefe→admin, Encargado→encargado, Auxiliar→auxiliar, Tecnico→invitado (mínimo privilegio;
  rol desconocido → invitado). `Usuarios.Activo=false` → perfil `activo=false`.
  `decano` no tiene equivalente en Usuarios por ahora.

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
- [x] T2 API base: CORS para Angular dev, dependencia de sesión con contexto de usuario,
      mapeo de roles, `GET /api/asignacion/me`.
- [x] T3 Auth en Angular: login contra `/api/auth/login`, interceptor JWT, proxy dev a 5013.
- [x] T4 Catálogos (ambientes, ambiente_pcs, materias, carreras, docentes, feriados, bloques…).
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

- T2 (delegado, writer): `CORS_ORIGINS` (vacío = sin middleware, prod igual; upds compose
  = localhost/127.0.0.1:4200), `services/asignacion_perfiles.py` (`map_role`, `ensure_perfil`
  upsert por usuario_id, adopta perfil huérfano por correo), `db/asignacion.py`
  (`get_asignacion_db`: sync+commit del perfil ANTES de fijar contexto — el trigger
  `fn_trg_proteger_admin` bloquearía la degradación si corre "como uno mismo" —; luego
  `set_config('app.usuario_id', id, true)` re-aplicado en cada transacción vía evento
  `after_begin`, así sobrevive a commits a mitad de request), router `/api/asignacion/me`
  (lee vía `fn_usuario_actual()`/`fn_rol_actual()`). Evidencia: RED (import error) →
  `pytest test_asignacion_base + test_horarios_schema + test_health` 23 passed en
  `soporte_upds_test`; ruff check/format OK; smoke en api 5013: login 200, /me sin token 401,
  /me Jefe 200 rol=admin, preflight Origin :4200 → allow-origin + credentials, origen ajeno 400.

- T3 (delegado, writer): `core/auth.service.ts` reescrito contra FastAPI (POST `/api/auth/login`,
  JWT en localStorage `upds.token`, perfil desde GET `/api/asignacion/me` → `Perfil` con
  `id = perfil_id`, rol null/desconocido → `invitado`; API pública igual: `sesion`, `perfil`,
  `listo`, `es*`, `puede*`, `inicializar`, `recargarPerfil`, `iniciarSesion`, `cerrarSesion`;
  nuevo `sesionExpirada()`), `core/auth.interceptor.ts` (Bearer solo a `apiUrl`; 401 fuera de
  login → limpia token y va a /login), `provideHttpClient(withInterceptors)` en app.config,
  `environment.apiUrl = '/api'`, `proxy.conf.json` `/api` → 127.0.0.1:5013 en `serve.options`.
  Backend sin logout: cerrar sesión = descartar JWT.
  Decisión: login con Google eliminado (Soporte_Tecnico no tiene OAuth); solo correo+contraseña.
  Quedan textos "entraron con Google" en `catalogos/usuarios.component.ts` y `modelos.ts` (T4).
  Test-first: excepción — el proyecto no tiene runner (sin target `test` en angular.json ni
  vitest instalado); checks funcionales. Evidencia: `npm ci` OK; `ng build` OK sin warnings;
  `ng serve` + proxy: `/api/asignacion/me` sin token 401, login Jefe 200, `/me` con token 200
  (rol=admin); UI (Playwright): `/` → `/login`, sin botón Google, contraseña errónea →
  "Correo o contraseña incorrectos." sin redirección.

- T4 (delegado, writer): `routers/asignacion/catalogos.py` (incluido por el router asignacion),
  `services/asignacion/sql.py` (permisos vía `horarios.fn_puede_*`, escrituras con columnas = campos
  Pydantic `extra=forbid`, valores ligados; errores PG → `detail={message,code,hint}`: 23505/23503→409,
  23514/23502/22xxx/P0001→422, 42501→403), `schemas/asignacion_catalogos.py`.
  Endpoints `/api/asignacion`: GET/POST `/carreras`, PATCH/DELETE `/carreras/{id}`; idem `/materias`,
  `/docentes` (con `docente_carreras`/`docente_materias` embebidos) + PUT `/docentes/{id}/relaciones`
  (reemplazo atómico); GET(`?tipo=`)/POST `/ambientes`, PATCH/DELETE `/ambientes/{id}`; GET(`?ambiente_id=`)/POST
  `/ambiente-pcs`, PATCH/DELETE `/ambiente-pcs/{id}` (embed `cambio{nombre_completo}`); GET `/sistemas-academicos`
  (activos), `/bloques-horario`, `/tipos-reserva`; GET `/feriados`, PUT/DELETE `/feriados/{fecha}` (upsert).
  Permisos = RLS: leer `fn_puede_ver` (invitado → 403; el invitado nunca llega al layout), escribir
  `fn_puede_editar`; PCs crear/editar `fn_puede_operar`, borrar `fn_puede_gestionar_auxiliares`.
  Front: `core/api.service.ts` (HttpClient → promesas, error → `ErrorSistema` con el mismo `code`, así
  los mensajes traducidos no cambian), `catalogos.service.ts` sin supabase (misma API pública + nuevo
  `guardarRelacionesDocente`), `catalogos/docentes.component.ts` sin supabase.
  Evidencia: RED 19 fallan (404) → GREEN; `pytest test_asignacion_catalogos + base + horarios_schema +
  health` 42 passed en `soporte_upds_test`; ruff check/format OK; `ng build` OK sin warnings; `ng serve`
  + proxy como Jefe: los 9 GET → 200 con datos seed (carreras, LAB-01.., bloques, feriados…), sin token 401.
  Pendiente: chequeo visual con Playwright (denegado por el clasificador de credenciales al inyectar el
  token); queda para revisión manual.
  Fuera de T4 (siguen con supabase): `asignacion-form.vincularDocente` (upsert docente_materias/carreras → T5,
  puede usar `PUT /docentes/{id}/relaciones` o un endpoint de vínculo), `rpc_cambiar_estado_pcs` en
  `panel/laboratorio-equipos` + `operacion.service` (T6), `catalogos/usuarios.component.ts` (gestión de
  usuarios = Soporte_Tecnico, otro agente). `ErrorSistema` sigue en `supabase.service.ts`: moverlo en T8.

## Siguiente paso
T5 Asignaciones, cesiones, reservas, reubicaciones + RPC de choques/ocupación.
