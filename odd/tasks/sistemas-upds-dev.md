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
  Jefe→admin, Encargado→encargado, Auxiliar→auxiliar, Decano→decano, Invitado→invitado,
  Tecnico→invitado (mínimo privilegio; rol desconocido → invitado). `Usuarios.Activo=false` →
  perfil `activo=false`. (T8: Soporte pasa a 6 roles; antes `decano` no tenía equivalente.)
- Permisos de Decano/Invitado en Soporte: **pendientes de definir**. Hasta entonces ningún chequeo
  les da nada: se comportan como el rol base (Técnico) sin privilegios y no figuran como técnicos.

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
- [x] T6b Operación: atenciones, fallas_pc, solicitudes_baja, objetos_perdidos (+ bucket), rpc_cambiar_estado_pcs,
      rpc_resolver_baja, rpc_registrar_reparaciones, fn_limpiar_fotos_objetos, `misBajasDesde` (ambiente_pcs) y
      los dos pendientes de T5 (`compartido/ocupacion-detalle`, `panel/laboratorio-detalle`).
- [x] T7 Dashboards (`fn_dashboard_*`).
- [x] T8 (alcance ampliado por el usuario 2026-10-09) Roles Decano e Invitado en Soporte (6 roles);
      pantalla de usuarios de horarios sobre los usuarios de Soporte; quitar Supabase del frontend
      (`@supabase/supabase-js`, `core/supabase.service.ts`, `environment.supabase*`).

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

- T6b (delegado, writer): `routers/asignacion/operacion.py` + `objetos_perdidos.py`, `schemas/asignacion_operacion.py`,
  `services/asignacion/fotos.py` generalizado por carpeta (`reportes-turno` | `objetos-perdidos`, prefijo `objetos/` o
  `entregas/`) + `servir()` (descarga privada no-store). Endpoints `/api/asignacion`: GET `/atenciones` (`?desde=&hasta=`
  días La Paz, `?estado=`, `?ambiente_id=`, `?participante=` autor o colaborador), GET `/atenciones/arrastradas` (pendiente/
  en_proceso por prioridad, pase de turno), POST `/atenciones` (lista → `[{id, pc_id}]`), PATCH `/atenciones` (`{ids, cambios}`),
  PATCH `/atenciones/{id}`, DELETE `/atenciones?id=` (repetible); POST `/ambiente-pcs/estado` (`rpc_cambiar_estado_pcs`),
  GET `/ambiente-pcs/mis-bajas?desde=`, POST `/ambientes/{id}/pcs/generar` (`fn_generar_pcs`); GET/POST `/fallas-pc`,
  PATCH `/fallas-pc/{id}`; POST `/reparaciones` (`rpc_registrar_reparaciones`); GET `/solicitudes-baja` (`?estado=`
  pendiente por defecto), POST `/solicitudes-baja` (lista), POST `/solicitudes-baja/{id}/resolver` (`rpc_resolver_baja`);
  GET `/objetos-perdidos` (`?limite=300`), POST `/objetos-perdidos` (multipart con foto), POST `/objetos-perdidos/{id}/entrega`
  (multipart con foto), DELETE `/objetos-perdidos/{id}`, GET `/objetos-perdidos/{id}/fotos/{objeto|entrega}`,
  POST `/objetos-perdidos/fotos/limpiar` (`fn_limpiar_fotos_objetos` + borra archivos). Embeds iguales a PostgREST.
  Permisos = RLS: leer `fn_puede_ver`; atenciones y objetos crear/editar `fn_puede_operar` (predicado solo de rol: un chequeo
  cubre USING y WITH CHECK); fallas_pc, borrar objeto y resolver baja `fn_puede_gestionar_auxiliares`; solicitud de baja
  `operar ∧ estado='pendiente'` (el esquema solo acepta 'pendiente', otro → 422, y se escribe explícito). El estado de PCs
  nunca se actualiza directo: solo las RPC fijan `app.cambio_estado_pc`. Las RPC validan rol, la API lo chequea antes (403).
  Fotos de objetos: misma validación/WebP que T6a, el servidor guarda foto y fila en una petición (si la fila falla se borra
  el archivo); borrar archivos = solo vía borrar fila (gestionar) o limpieza (rutas ya sin fila, como la política de storage).
  Front: `operacion.service.ts` sin supabase (mismos métodos + `generarPcs`), `objetos-perdidos.component.ts` (blobs con
  Bearer, 6 descargas simultáneas, revoca URLs), `panel/laboratorio-equipos` (generar/cambiar estado vía OperacionService),
  `panel/laboratorio-detalle` (`AsignacionesService.listar({ambienteId, finDesde})`), `compartido/ocupacion-detalle`
  (`eliminarReubicacion`). Cambio menor: filtro desde/hasta de atenciones usa días de La Paz (antes UTC de PostgREST).
  Evidencia: RED 13 fallan → GREEN 13; `pytest test_asignacion_* + horarios_schema + health` 89 passed en
  `soporte_upds_test` (sin filas residuales, fotos en tmp_path); ruff check/format OK; `ng build` OK sin warnings; curl
  5013 como Jefe: GET atenciones, arrastradas, fallas-pc, solicitudes-baja, objetos-perdidos, mis-bajas, asignaciones
  `?ambiente_id=` → 200, POST limpiar 200, sin token 401; proxy ng serve 4200 sin token 401.
  Supabase restante: `desempeno.component.ts` (`fn_dashboard_*`, T7), `catalogos/usuarios.component.ts` (otro esfuerzo),
  `core/supabase.service.ts` (T8). Tamaño ~1.45k líneas (570 tests): excede la heurística por 4 tablas + 5 funciones + fotos.

- T7 (delegado, writer): `routers/asignacion/dashboards.py`, `services/asignacion/dashboards.py` (lista blanca `Dashboard`
  → `horarios.fn_dashboard_<nombre>(:desde, :hasta)` ligado; error PG → mismo mapeo del módulo), `schemas/asignacion_dashboards.py`
  (`RangoDashboard` como modelo Query: `hasta >= desde` y `hasta - desde <= 400` → 422, igual que las funciones).
  Endpoint `/api/asignacion`: GET `/dashboard/{operacion|uso|detalle|fallas}?desde=&hasta=` → el JSON de la función tal cual.
  Permisos = funciones SQL: las cuatro exigen `fn_puede_gestionar_auxiliares` (admin/encargado); la API lo chequea antes (403
  `42501`). `fn_dashboard_operacion` cuenta el rango inclusivo (`v_dias > 400`): ese borde lo rechaza la función → 422 `P0001`.
  Front: `desempeno.component.ts` sin supabase (`ApiService.get` vía `leerDashboard`; mismas interfaces). `paneles.service.ts`
  no se tocó: es la pila de paneles laterales, no dashboards.
  Test-first: el test RED previo se mantuvo sin cambios (coincide con las funciones); se agregó el borde 400 días de operacion.
  Evidencia: RED 33 fallan (404) → GREEN 34; `pytest test_asignacion_* + horarios_schema + health` 123 passed en
  `soporte_upds_test` (vía `podman exec soporte-upds_api_1 python -m pytest` con DATABASE_URL → `soporte_upds_test`; sin filas
  residuales); `ruff check .` OK; `ruff format --check` OK en los archivos del módulo (el backend completo ya tenía 43 archivos
  sin formato ajenos a esta rama); `ng build` OK sin warnings; curl 5013 sin token → 401 en los 4. Smoke autenticado no hecho
  (sin contraseña de prod en esta sesión).
  Supabase restante: `catalogos/usuarios.component.ts` (otro esfuerzo), `core/supabase.service.ts` (T8).

- T8 (delegado, writer). Cambio de alcance aprobado por el usuario: además de quitar Supabase, (1) Soporte suma los
  roles Decano e Invitado y (2) la pantalla `catalogos/usuarios` gestiona los usuarios de Soporte, porque `Usuarios`
  es la única fuente de identidad y crear cuentas en `perfiles` ya no tiene sentido sin `auth.users`.
  Commit 1 `0572374` feat(usuarios): `ROLES_VALIDOS` + `ROL_INVALIDO` (6 roles), `ROLE_MAP` Decano→decano,
  Invitado→invitado; select de roles de Django (`usuarios_vista`); README tabla de roles (permisos pendientes).
  Decano/Invitado sin privilegios en Soporte: no son `is_privileged`, ni Encargado ni Auxiliar; Django los trata
  como el rol base (panel Soporte). Test-first: `tests/test_usuarios_roles.py` RED 7 fallan / 6 pasan (los 403 y
  "no listado como técnico" ya pasaban: son guardas) → GREEN 13. Django: smoke con `manage.py shell` + test Client
  y API mockeada como Decano/Invitado: `/`, `/atenciones/`, `/perfil/` 200; `/usuarios/`, `/dashboard/`,
  `/auxiliares/` 302 → `/atenciones/` (sin crash). `manage.py test tests` 38 tests, 3 fallas iguales en la base.
  Commit 2 feat(asignacion): `routers/asignacion/usuarios.py` + `schemas/asignacion_usuarios.py`. Endpoints
  `/api/asignacion`: GET `/usuarios` (sincroniza un perfil por cada usuario de Soporte con `ensure_perfil`, un
  savepoint por usuario; devuelve perfil + `usuario_id` + `role` de Soporte, ordenado por nombre; perfiles huérfanos
  sin `usuario_id` no se muestran), POST `/usuarios` (rol admin|auxiliar|decano|encargado como `fn_crear_usuario`,
  invitado → 422), PATCH `/usuarios/{perfil_id}` (rol, activo, nombre_completo → `Usuarios`; turno_habitual,
  sabado_rotativo → `horarios.perfiles`; luego re-sync), POST `/usuarios/{perfil_id}/password` (204).
  Decisión: endpoint fino en vez de llamar `/api/usuarios` desde Angular — la pantalla necesita perfil_id, correo y
  campos de horarios junto a la identidad, y la traducción rol↔Role (con la regla del Técnico) vive en el servidor
  junto a `ROLE_MAP`. Sin duplicar lógica: `routers/usuarios.py` expone `crear`, `aplicar_rol`, `aplicar_activo`,
  `aplicar_password`, `aplicar_nombre`, `buscar_usuario` (validan y mutan; sin commit ni permisos) y los handlers de
  `/api/usuarios` los usan también. Traducción `ROL_TO_ROLE`: admin↔Jefe, encargado↔Encargado, auxiliar↔Auxiliar,
  decano↔Decano, invitado↔Invitado. Técnico: se muestra como `invitado` con chip "Técnico de Soporte"; el Role solo
  se escribe si el rol pedido difiere de `map_role(Role actual)`, así guardar "invitado" (o solo el turno) no lo
  degrada; cambiarlo a otro rol pide confirmación en la UI porque deja de ser Técnico en Soporte.
  Permisos: admin (`fn_es_admin`) para listar, crear, editar y contraseña = `fn_crear_usuario`/`fn_cambiar_password`/
  `perfiles_editar`; admin = Jefe, que también cumple la regla de Soporte (`is_privileged`). Listar también es solo
  admin (antes `perfiles_ver` = `fn_puede_ver`): expone correos de todo Soporte y la pantalla ya era solo admin.
  Propio rol / desactivarse → 400 (regla de Soporte; equivale a `fn_trg_proteger_admin`).
  Front: `core/usuarios.service.ts` (listar/crear/actualizar/cambiarPassword), `UsuarioSistema` en `modelos.ts`,
  `usuarios.component.ts` sin supabase (misma UI; aviso "entraron con Google" → "sin acceso a este sistema
  (Invitado o Técnico de Soporte)"). Supabase fuera: `ErrorSistema` → `core/errores.ts` (sin los códigos `PGRST*`,
  que ya nadie produce), `supabase.service.ts` borrado, `npm uninstall @supabase/supabase-js`, `environment.supabase*`
  y aviso `sinConfigurar` del layout fuera, comentarios de `api.service.ts`/`modelos.ts` limpios.
  Evidencia: RED `test_asignacion_usuarios.py` 23 fallan / 1 pasa (404 trivial) → GREEN 24; `pytest
  test_asignacion_usuarios + test_usuarios_roles` 37 passed en `soporte_upds_test`; suite completa 211 passed, 90 failed,
  39 errors = mismas 90+39 fallas que la base 57680e3 (174 passed) — usuarios sembrados de prod (id 8, correos) que
  la base de test no tiene; `ruff check .` OK; `ruff format --check` OK en los 7 archivos Python tocados/nuevos;
  `ng build` OK sin warnings; `rg -i supabase frontend-horarios/src frontend-horarios/package.json` vacío (lock sin
  supabase); curl 5013 sin token → 401 en GET/POST `/usuarios`, PATCH `/usuarios/{id}`, POST `/usuarios/{id}/password`.
  Smoke autenticado no hecho (sin contraseña de prod en esta sesión).
  Pendiente: definir permisos de Decano/Invitado en Soporte; `frontend-horarios/supabase/` (SQL de referencia) queda.

## Siguiente paso
Feature completa (T1–T8). Siguiente: revisión manual en navegador (pantalla de usuarios con un Jefe), definir permisos
de Decano/Invitado en Soporte, y decidir entrega (PRs encadenados por `ask-on-risk`).
