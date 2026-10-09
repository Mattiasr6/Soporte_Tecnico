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
- [x] T5 Asignaciones, cesiones, reservas, reubicaciones + RPC de choques/ocupación.
- [x] T6a Turnos y reportes de turno: turnos_programados, turnos_trabajo, horarios_turno, rotacion_sabados,
      perfiles de operación, fn_turno_vigente/fn_asignar_turno, reportes_turno + reporte_tareas + foto de cierre.
- [x] U1 Integrar upstream d0d7ad1 (UI móvil + reubica en choques, SQL 34 → 0022).
- [ ] T6b Operación: atenciones, fallas_pc, solicitudes_baja, objetos_perdidos (+ bucket), rpc_cambiar_estado_pcs,
      rpc_resolver_baja, rpc_registrar_reparaciones, fn_limpiar_fotos_objetos, `misBajasDesde` (ambiente_pcs) y
      los dos pendientes de T5 (`compartido/ocupacion-detalle`, `panel/laboratorio-detalle`).
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

- T5 (delegado, writer): `routers/asignacion/horarios_academicos.py` + `ocupacion.py`, `schemas/asignacion_horarios.py`,
  `services/asignacion/sql.py::call_rpc` (payload JSON ligado como un solo `jsonb`, nombre de función literal).
  Escrituras = RPC SQL existentes (no se reimplementa lógica) dentro de `writing()` → el commit dispara los
  triggers anti-choque diferidos y su error vuelve como 422 `P0001` con el mensaje del trigger.
  Endpoints `/api/asignacion`: GET `/asignaciones` (`?fin_desde=` fecha del cliente, `?ambiente_id=` estilo `!inner`),
  GET/PUT/DELETE `/asignaciones/{id}`, POST `/asignaciones` (`rpc_guardar_asignacion`); GET `/cesiones`
  (`?lote=`, `?excluir_lote=`, `?asignacion_horario_id=` repetible), GET/DELETE `/cesiones/{id}`, POST `/cesiones/lotes`,
  PUT `/cesiones/lotes/{lote}` (`rpc_guardar_cesiones`); GET/POST `/reservas`, GET/PUT/DELETE `/reservas/{id}`
  (`rpc_guardar_reserva`); POST `/reubicaciones` (`rpc_reubicar_clase`), DELETE `/reubicaciones/{id}`;
  GET `/ocupaciones`, `/conflictos`, `/estado-ambientes`; POST `/choques/verificar`, `/ambientes-libres`,
  `/ambientes-libres/fechas` (cuerpo tipado, solo lectura); POST `/docentes/{id}/vinculos` (agrega sin reemplazar,
  para `vincularDocente`). Embeds iguales a los selects PostgREST (docente, materia, carrera, horarios, fechas;
  receptor, horario.asignacion; tipo, reubicaciones).
  Permisos = RLS: leer `fn_puede_ver`, escribir/borrar `fn_puede_editar` (las RPC no validan rol; auxiliar → 403).
  Front: `core/ocupacion.service.ts` (misma API pública + `eliminarReubicacion`), nuevo `core/asignaciones.service.ts`
  (listas/detalle/borrado de asignaciones, cesiones, reservas), `catalogos.service.vincularDocente`; páginas
  asignaciones/cesiones/reservas sin supabase.
  Evidencia: RED 14 fallan (404) → GREEN; `pytest test_asignacion_horarios_academicos + catalogos + base +
  horarios_schema + health` 56 passed en `soporte_upds_test` (sin filas residuales); ruff check/format OK;
  `ng build` OK sin warnings; `ng serve` + proxy como Jefe: GET asignaciones/cesiones/reservas/ocupaciones/
  conflictos/estado-ambientes y POST ambientes-libres/choques → 200, sin token 401.
  Tamaño: ~1.2k líneas (mitad tests); excede la heurística de 400 de forma natural (5 tablas + 6 funciones).
  Pendiente fuera de superficie: `compartido/ocupacion-detalle.component.ts` (borra `reubicaciones` vía supabase →
  usar `ocupacion.eliminarReubicacion(id)`) y `panel/laboratorio-detalle.component.ts` (`.from('asignaciones')` con
  `!inner` por ambiente → `AsignacionesService.listar({ ambienteId, finDesde: hoyIso() })`).

- T6a (delegado, writer): `routers/asignacion/turnos.py` + `reportes.py`, `schemas/asignacion_turnos.py`,
  `services/asignacion/fotos.py`, setting `ASIGNACION_DATA_DIR` (vacío = `backend-fastapi/data/asignacion`, ignorado en
  git y docker). Endpoints `/api/asignacion`: GET/PUT `/turnos-programados` (upsert perfil_id+desde), DELETE `/{id}`;
  GET `/turnos/vigente` (`fn_turno_vigente`, por defecto uno mismo y hoy La Paz); GET/PUT `/horarios-turno`;
  GET `/auxiliares` (`?rol=` repetible, `?activo=`), PUT `/auxiliares/{perfil_id}/turno` (`fn_asignar_turno`);
  GET/POST `/rotacion-sabados`, PATCH/DELETE `/{id}`; GET `/turnos-trabajo/estado`, POST `/turnos-trabajo`,
  POST `/turnos-trabajo/{id}/cierre`; GET/POST `/reportes-turno` (reporte + tareas en una transacción),
  PATCH/DELETE `/reportes-turno/{id}`, PUT `/reportes-turno/{id}/tareas` (reemplaza pendientes), GET
  `/reporte-tareas/pendientes`, PATCH `/reporte-tareas/{id}` (hecha; hecha_por = quien pide); POST/GET/DELETE
  `/reportes-turno/{id}/foto`, POST `/reportes-turno/fotos/limpiar` (`fn_limpiar_fotos_reporte` + borra archivos).
  Permisos = RLS: leer `fn_puede_ver`; programados/rotación/horarios/asignar turno `fn_puede_gestionar_auxiliares`;
  turnos_trabajo y marcar tarea `fn_puede_operar`; crear reporte `operar ∧ (propio ∨ gestionar) ∧
  fn_puede_cerrar_turno(turno)`; editar/borrar reporte y crear/borrar tareas `fn_puede_editar_reporte(id)` evaluado
  antes (USING) y otra vez sobre la fila escrita antes del commit (WITH CHECK). `perfiles_propio` lo cubre `/me`.
  Fotos: JPG/PNG/WEBP ≤ 5 MB (415/413/422), Pillow → WebP, nombre `YYYY-MM/<uuid>.webp` generado por el servidor,
  rutas resueltas dentro de la carpeta; descarga autenticada (sin URLs firmadas): Angular la baja como blob con el
  Bearer y usa `URL.createObjectURL` (`firmarFotosReporte(reportes)`); subir/borrar = `fn_puede_editar_reporte`.
  Front: `operacion.service.ts` (mismos métodos públicos; atenciones/fallas/bajas/`misBajasDesde` siguen en supabase
  para T6b), `api.service.ts` (+`getBlob`, `postForm`, params array), `turno.component.ts` (pasa reportes a
  `firmarFotosReporte`). Crear reporte con foto = POST reporte + POST foto; si la foto falla se borra el reporte.
  Evidencia: RED 16 fallan + 3 errores → GREEN; `pytest test_asignacion_turnos + horarios_academicos + catalogos +
  base + horarios_schema + health` 75 passed en `soporte_upds_test` (sin filas residuales, horarios_turno restaurado,
  fotos en tmp_path); ruff check/format OK; `ng build` OK sin warnings; curl en api 5013 como Jefe: los 8 GET → 200,
  sin token 401.

- U1 (delegado, writer): upstream ASIGNACION_DE-HORARIOS `d0d7ad1` aplicado con
  `git format-patch` + `git apply -3 --directory=frontend-horarios`: los 17 archivos entraron sin conflictos
  (styles.css y laboratorio-detalle por aplicación directa, blob ambiguo). Resolución: el único uso supabase nuevo
  (`asignacion-form.cargarReubicaciones`, `.from('reubicaciones')`) pasa a `OcupacionService.listarReubicaciones`
  → nuevo GET `/api/asignacion/reubicaciones?asignacion_horario_id=` (repetible, `fn_puede_ver` = RLS
  `reubicaciones_ver`). Resto de cambios UI/móvil tomados tal cual (docentes/turno/auxiliares sin cambios de datos).
  SQL 34 copiado a `frontend-horarios/supabase/` y portado en migración `0022_horarios_reubica_choques`
  (`alembic/sql/0022_horarios/01_rpc_guardar_asignacion.sql`; downgrade restaura la versión 0021 desde
  `down_01_...sql`): `rpc_guardar_asignacion` acepta `p.reubicaciones` y guarda los días ocupados en otro
  laboratorio/aula en la misma transacción. Misma firma; el POST/PUT `/asignaciones` ya reenvía el JSON (sin cambio
  de endpoint). Script 34 no tiene RLS/grants/auth/storage: nada descartado.
  Evidencia: RED (test nuevo `test_asignacion_moves_busy_days_to_another_ambiente` falla en 0021) → GREEN;
  upgrade/downgrade 0021 (vuelve a fallar)/upgrade OK en `soporte_upds_test`; `pytest test_asignacion_* +
  horarios_schema + health` 76 passed; `soporte_upds` en 0022; ruff check/format OK; `ng build` OK sin warnings;
  usos `.from/.rpc/.storage` iguales antes/después (ninguno nuevo); curl 5013 Jefe GET `/reubicaciones` 200, sin
  token 401; proxy ng serve 4200 401 sin token.

## Siguiente paso
T6b Operación (atenciones, fallas_pc, bajas, objetos perdidos + fotos, RPC de PCs/reparaciones) y los dos usos
supabase pendientes de T5 (`compartido/ocupacion-detalle`, `panel/laboratorio-detalle`).
