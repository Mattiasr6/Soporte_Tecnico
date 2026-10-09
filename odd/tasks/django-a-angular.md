# Django → Angular migration (strangler fig)

Locator: `odd/tasks/django-a-angular.md` · Engram mirror: `odd/django-a-angular/tasks` (project `soporte_tecnico`)
Branch: `feat/sistemas-upds-dev` · Stack for checks: UPDS dev (`deploy/podman/upds.compose.yml`, Angular at :4213)

## Objective

Move every screen of the Django SSR frontend (`frontend-django/`) into the Angular app
(`frontend-horarios/`) one business area at a time, then shut Django down. One frontend
(Angular) + one backend (FastAPI) for the whole UPDS ecosystem.

## Why

Team decision (2026-10-09): 2 backend devs + 1 UI/UX designer who works in Angular.
Angular already holds the interactive screens (day grid, side panels, dashboards) and both
frontends already talk to the same FastAPI, so only the presentation layer must merge.

## Constraints

- Prod and the dev stack (8011) are never touched; work and checks run on the UPDS stack.
- **Version decisions are the user's.** Whenever a screen depends on a duplicated domain
  (old Soporte table vs `horarios.*`), stop and ask which one stays before migrating it.
- Django keeps working for every area not migrated yet; nothing is deleted from Django until
  its area is complete in Angular and the user approves.
- Container/presentational split: presentational components take `input()`/`output()` only
  (designer-owned surface); containers and services own API calls, state and role rules.
- Artifacts (code, comments, UI copy) follow the existing Angular app: Spanish UI copy,
  English comments.

## Map (explorer, 2026-10-09)

- Django: 66 routes in `frontend-django/atenciones/urls.py`, every call goes through
  `atenciones/api.py` to FastAPI with the JWT kept in the Django session.
- Angular only calls `/api/asignacion/*` and `/api/auth/login` (`core/api.service.ts:8`).
- Django-only logic to rebuild per area: report/chart computations (`views.py` `_graficos`,
  `_kpis_reporte`…, `views_lab.py` `_payload_lab_dashboard`, board, timeline), the attention
  batch draft and Wilmercito history in session, and the auxiliar "soy" identity that becomes
  the author of lab records.
- `/ws` realtime has no frontend consumer; prod Caddy only proxies `/api/*`.
- Media: `ASIGNACION_DATA_DIR` (asignacion photos) and hardcoded `data/aux_reportes`
  (novedades photos); prod persists both only via `appdata-prod:/app/data`. Future goal: NAS.

## Pending user decisions (block their areas)

- ~~D1–D4~~ → decided 2026-10-09 ("mejor preservar angular"): whenever Django and Angular
  overlap, the Angular/horarios version stays. D1 `horarios.ambientes`/`ambiente_pcs`,
  D2 `horarios.atenciones`, D3 `horarios.perfiles` + `M/MD/T/N`, D4 `horarios.reportes_turno`
  + `objetos_perdidos`. Django-only features are ported onto the horarios tables; the old
  Soporte tables become read-only sources for a later data migration (131 LabAtenciones).
- ~~D5 Angular role model~~ → decided 2026-10-09: Soporte's 6 roles are the single model in
  Angular; Tecnico gets a real horarios role (see R1/R2).

## Tasks

- [x] M0 Groundwork: Angular client for non-`/asignacion` FastAPI routes (second base in
  `core/`), plus a "Mi cuenta" entry in the layout menu. Route: delegated (multi-file).
- [x] M1 Perfil: view/edit display name and change password (re-login after change, as
  Django `perfil_guardar_vista`). Uses `/api/usuarios/me`. Route: delegated with M0.
- [x] M2 Notas personales: GET/PUT `/api/usuarios/notas`. Route: delegated with M0.
- [x] R1 D5 backend (decided 2026-10-09): real `tecnico` horarios role. Tecnico sees everything
  and operates like auxiliar (atenciones, reparaciones, PC states, baja requests; the single
  OPERAR permission also covers turnos/objetos, accepted). No academic edit, no management,
  no personal shift. Migration 0023, `ROLE_MAP` Tecnico→tecnico, `/asignacion/me` exposes the
  Soporte `Usuarios.Role`. Route: delegated (multi-file).
- [x] R2 D5 Angular: Soporte roles (Tecnico, Jefe, Auxiliar, Encargado, Decano, Invitado) are the
  single role model; guards, menu and user screen read `Usuarios.Role`. Invitado stays
  "pending, no access" (/espera). Route: delegated with R1.
- [x] M3 Auditoría (read-only, Jefe or dashboard flag): `/api/auditoria`. Route: delegated with M4.
- [x] M4 Soporte attentions list + ticket (D5 resolved). Route: delegated with M3.
- [x] M5 Gap map (explorer, 2026-10-09; Engram #126). Ports onto horarios, smallest first:
  - [x] G1 (S) Printable lab-attention ticket; clone an attention into N labs.
  - [x] G2 (S) Objetos "vencido" state (computed, 90 days); encargado toggle on the team screen.
  - [x] G3 (M) Turno code + `medio_solicitud` on `horarios.atenciones`; dashboard per lab × category/turno; reports turno filter.
  - [ ] G4 (M) Tablero semáforo + day timeline (union over atenciones/reportes/objetos, no new table).
  - [ ] G5 (M) Novedades per lab + cierre validation (`ambiente_id`, `estado`, `validado_por` on `reportes_turno`).
  - [ ] G6 (M) Saturday hours per date and several auxiliares per turno; XLSX/PDF schedule export.
  - [ ] G7 (L) Software inventory (`horarios.software`, `ambiente_software`, `pc_software`, attention templates).
  - [ ] G8 (L) Lab hardware sheet columns on `ambientes`; free fila/col room grid (or keep the 4-PC table layout).
  - [ ] M4b Soporte "Nueva atención" (Django keeps a session batch draft + Wilmercito suggestion).
- [ ] M6 Data migration: LabAtenciones (131) → `horarios.atenciones`, aux JSON → perfiles.
- [ ] Later areas (dashboards, reports, jerarquía, IA) are added as tasks per slice.

## Acceptance (per slice)

- The Angular screen does everything the Django one does for the same roles.
- `ng build` passes in the horarios image; existing Angular tests stay green.
- Smoke check on :4213 with a real login; Django screen still works until retired.

## Delivery

Strategy: ask-on-risk. Forecast M0–M2 ≈ 400 authored lines. RDD disabled for this clone.

## Progress

- 2026-10-09: map done, doc created.
- 2026-10-09: M0–M2 done (route: delegated, one writer; trigger: 2+ non-trivial files).
  Commit `5a2a2ed` feat(horarios): add Mi cuenta profile and notes pages.
  - M0: `ApiRaizService` (subclass of `ApiService`, base `/api`) reuses `ErrorSistema` handling;
    the interceptor already covers every `/api/*` URL. Exempted `/api/auth/password` from the
    401 → logout rule (wrong current password answers 401). "Mi cuenta" section in the menu
    (all roles), routes `/cuenta/perfil` and `/cuenta/notas`.
  - M1: `/api/usuarios/me`, PATCH `/api/usuarios/{id}/especialidad` (backend: Jefe or
    dashboard viewers only, same as Django), POST `/api/auth/password`; the backend bumps
    `token_version`, so the page re-logs in via `AuthService.iniciarSesion(correo, nueva)`;
    if that fails the session is dropped and the user goes to login.
  - M2: GET/PUT `/api/usuarios/notas`, autosave after 1.2 s idle, on blur, on leaving the page
    and on `beforeunload`, with the same status indicator as `notas.js`.
  - Not migrated: the Perfil "Accesibilidad" block (letter size/contrast/motion in
    localStorage) needs global CSS classes in `src/styles.css`, outside this slice; the
    "estadísticas etapa 2" placeholder was skipped.
  - Note: Soporte `Tecnico` users mapped to Angular `invitado` (D5) at that time; fixed by R1/R2.
  - Checks: horarios image build → "Application bundle generation complete", no errors;
    login as paul → GET `/api/usuarios/me` 200, GET `/api/usuarios/notas` 200; POST
    `/api/auth/password` with a wrong current password → 401 (confirms the exemption is
    needed; password not changed); `/cuenta/perfil` and `/cuenta/notas` → 200 (SPA fallback);
    `cuenta/perfil` present in the served `main-*.js`. No spec files exist (test-first
    exception); no browser click-through was done.
- 2026-10-09: R1–R2 done (route: delegated, one writer; trigger: 2+ non-trivial files across
  backend and Angular). Commits `fbdfc46` feat(asignacion): give Tecnico a real horarios role,
  and the R2 commit feat(horarios): use Soporte roles as the Angular role model.
  - R1: migration `0023_horarios_rol_tecnico` (inline SQL, `_run_sql`): `perfiles_rol_check`
    + `tecnico`, `fn_puede_operar` + `tecnico`; downgrade turns tecnico perfiles back into
    invitado and restores both. `ROLE_MAP` Tecnico→tecnico, `ROL_TO_ROLE` is now its exact
    inverse; `RolAsignacion`, `RolNuevo` and the turnos `Rol` filter accept `tecnico`. The
    "Tecnico shows as invitado" special case in `routers/asignacion/usuarios.py` is gone; the
    "only write a real change" check stays (aplicar_rol refuses any self rol change).
    `/asignacion/me` also returns `role` (Usuarios.Role, joined on `perfiles.usuario_id`).
  - Tests that used a Tecnico as the "no access" user now use Invitado; new tests cover the
    tecnico permissions (schema), `/me` role, users-screen tecnico rol, and a Tecnico creating
    a ticket + changing a PC state while getting 403 on fallas-pc (GESTIONAR), feriados
    (EDITAR) and dashboards.
  - RED: 16 failed / 160 passed on the 9 asignacion test files before the code change.
    GREEN: 176 passed. Full suite: baseline 90 failed / 211 passed / 39 errors → after
    90 failed / 228 passed / 39 errors, same failing set (seed users missing in test DB).
  - Migration: dev DB upgrade → 0023 (head); round-trip downgrade -1 → 0022, upgrade → 0023.
    Test DB upgraded to 0023. Ruff check + format clean on touched files (host ruff; the
    container has none).
  - GitNexus impact: the index (other checkout) did not resolve `ensure_perfil`/`map_role`/`me`;
    manual check: `ensure_perfil` runs in `get_asignacion_db` (every asignacion request) and the
    users router; `/me` is only read by Angular `auth.service.ts`.
  - R2: `RolSoporte` + `ROLES_SOPORTE` + `ROL_DE_ROLE` in `core/modelos.ts`; `AuthService.role`
    (missing/unknown → Invitado, fail closed) drives every computed; new `esTecnico` and
    `puedeCerrarTurno` (manager or auxiliar: the technician has no shift, so the close-shift
    form is hidden for him while the turno page still lets him mark pending tasks). Users
    screen shows/assigns the 6 Soporte roles (service translates with `ROL_DE_ROLE`), Técnico
    confirmation removed. Collaborator list (`listarPersonalOperacion`) includes técnicos in a
    "Técnicos" group. Sidebar shows the Soporte role name; /espera copy talks about Invitado.
  - Checks: horarios image build → "Application bundle generation complete", no errors.
    Smoke as paul (Tecnico) on :4213: `/api/asignacion/me` 200 rol `tecnico` role `Tecnico`;
    `/api/asignacion/atenciones` 200 (403 before); `/auxiliares?rol=tecnico` 200;
    dashboard operacion 403. Browser: paul lands on `/` (no longer /espera) with menu Inicio,
    Cerrar turno, Atenciones, Objetos perdidos, Laboratorios, Registros, Mi cuenta. No Angular
    spec files exist (test-first exception for R2).
  - Known limitation: a técnico only appears in the collaborator list after he opened the
    Angular app once (perfiles are created lazily by `ensure_perfil`; the users screen syncs all).
- 2026-10-09: M3–M4 done (route: delegated, one writer; trigger: 2+ non-trivial files).
  Commits `35d7177` feat(horarios): add read-only audit trail screen, `069711a`
  feat(horarios): add Soporte attentions list and ticket.
  - M3: `/auditoria` (menu item "Auditoría", guard `exigirDashboard`). Django and the backend
    both allow Jefe **or** `Usuarios.CanViewDashboard` (`is_privileged`), which Angular could not
    see, so `/asignacion/me` now also returns `can_view_dashboard` (backend change, 4 lines) and
    `AuthService.puedeVerDashboard` mirrors it. Same filters (entidad, acción, limite 200) and
    columns (Cuándo, Quién + rol/#id, Acción, Entidad, Detalle). Files: `core/auditoria.service.ts`,
    `paginas/auditoria/auditoria.component.ts` (container), `auditoria-tabla.component.ts`
    (presentational), `History` icon as `historial`.
  - M3 tests: RED 2 failed / 17 passed on `tests/test_asignacion_base.py` (key set + new
    `test_me_exposes_can_view_dashboard_flag`), GREEN 19 passed; host ruff check + format clean.
  - M4: `/soporte/atenciones` under a new "Soporte" menu section (guard `exigirSoporte`:
    Jefe, Técnico, Decano = Django's "everyone but Auxiliar/Encargado"; Invitado never enters
    Angular). Same as `lista_vista`: GET `/api/atenciones` (backend: Jefe/dashboard see all,
    others their own), search on descripción/área, categoría and mes filtered client-side,
    técnico filter (Jefe/dashboard only, `usuario_id` server-side, users incl. "(de baja)"),
    columns Fecha, Área, Categoría, Técnico, Fuera de turno, "Ver más" +50 up to 500. Ticket in
    a modal; owner-only Editar (PUT `/api/atenciones/{id}`, area picker over
    `/api/jerarquia/arbol`, collaborators from `/api/usuarios`, empty fields omitted like
    `_cuerpo_edicion`) and Eliminar (DELETE, confirm). `Perfil.usuario_id` added for the owner
    check. Files: `core/soporte.service.ts`, `paginas/soporte/atenciones-soporte.component.ts`
    (container), `atenciones-soporte-tabla`, `ticket-soporte`, `ticket-soporte-form`
    (presentational).
  - M4 size: ~730 authored lines, over the 400 heuristic because list + ticket + edit form with
    the area picker form one behavior; not split.
  - Not migrated: "Nueva atención" (`nueva_vista`: session batch draft + Wilmercito
    suggestion), the hierarchy counts (`conteos_json`) in the area picker, and clearing a
    collaborator (the backend ignores `colaborador_id: null`, same as Django).
  - Checks: horarios image build → "Application bundle generation complete", no errors (both
    slices). Smoke on :4213: paul (Tecnico) `/asignacion/me` 200 `can_view_dashboard:false`,
    `/api/auditoria` 403; Jefe token (minted in the api container) `/api/auditoria` 200 with
    and without filters (0 rows in the UPDS DB). paul `/api/atenciones` 200 (584, own only),
    Jefe 200 (2936), Jefe `?usuario_id=3` 584; `/api/jerarquia/arbol` 200; `/api/usuarios` 200;
    `?incluir_inactivos=true` 200; PUT own (unchanged categoría) 204; PUT/DELETE another
    user's 403; DELETE missing 404. `/auditoria` and `/soporte/atenciones` → 200 (SPA) and in
    `main-*.js`. Browser as paul: list renders 584 rows, Soporte section in the menu, no
    Auditoría item, ticket modal and edit form open with the area preselected; 0 console
    errors. No Angular spec files exist (test-first exception for the Angular parts).
  - GitNexus `detect_changes` unavailable: the index is for another checkout.
- 2026-10-09: G1–G2 done (route: delegated, one writer; trigger: 2+ non-trivial files per task).
  Commits `64e9d0f` feat(horarios): add printable attention ticket and clone into labs,
  `8f52194` feat(horarios): show expired lost objects and toggle encargado role. No backend change.
  - G1 ticket: "Ver e imprimir ticket" on every record of `/atenciones` opens a modal with
    `ticket-atencion.component.ts` (presentational: folio, fecha, tipo, lab, autor,
    colaboradores, estado of the batch, prioridad, solicitante, PCs, descripción, detalle,
    solución). "Imprimir" adds `imprimiendo` to `<body>` and calls `window.print()`; the
    `@media print` rule in `src/styles.css` prints only `.zona-impresion` in black on white
    (normal page printing unchanged). New `imprimir` (Printer) icon.
  - G1 clone: "Clonar en otros laboratorios" (puedeOperar, tipos docente/programas/preventivo/
    personal) opens `clonar-atencion.component.ts` (presentational: edit descripción, solución,
    prioridad; 0–99 copies per lab, several per lab allowed, live count). The container sends one
    bulk POST `/api/asignacion/atenciones` with lab-level copies (same tipo, detalles, docente/
    solicitante, colaboradores; current turno; copier is the author). The bulk POST has no
    duplicate check (Django needed `forzar_duplicado` only on `/api/laboratorios`), so no backend
    change.
  - G1 left out: correctivo (changes PC states via fichas) and cambio_estado are not clonable;
    the copy date (Django `fecha_registro`) is not editable because `creado_en` is not writable
    in `AtencionIn`; the Django owner/encargado-only clone rule became Angular's puedeOperar,
    same as edit/delete on this screen.
  - G2 vencido: `core/objetos.ts` `estadoVisible` mirrors `routers/novedades.py`
    `_estado_efectivo` (still pending and more than 90 days since registration); the horarios
    backend has no 90-day rule (only the 9-month photo cleanup), so it is computed client-side on
    the La Paz calendar date of `encontrado_en`. `objeto-estado-chip.component.ts`
    (presentational) shows Vencido; new filter tab "Vencidos +90 días"; "En custodia" no longer
    counts them; Entregar stays available. Left out: Django's "Purgar vencidos" (horarios already
    deletes rows only for gestionar and clears photos after 9 months).
  - G2 encargado: section "Encargados" on `/auxiliares` with `encargados-equipo.component.ts`
    (presentational switch list of active auxiliares + encargados, `listarEquipo()`); the
    container PATCHes `/api/asignacion/usuarios/{perfil_id}` with rol encargado/auxiliar via
    `UsuariosService`. The endpoint is admin-only (`fn_es_admin` = Jefe), so the switch is
    enabled only for the Jefe; an Encargado sees it disabled with a note (Django let the
    Encargado toggle its JSON roster; the backend rule wins).
  - Checks: horarios image build → "Application bundle generation complete", no errors (both
    tasks); new strings present in the served lazy chunks. Smoke on :4213: paul `/asignacion/me`
    200, `/ambientes` 200, POST `/atenciones` origin 201, clone POST (2 in LAB-02 + 1 in LAB-03)
    201 → 3 rows, DELETE cleanup 204; Jefe (minted token) GET `/usuarios` 200 (syncs perfiles),
    `/auxiliares?rol=auxiliar&rol=encargado&activo=true` 200, PATCH rol as paul 403, as Encargado
    403, as Jefe → encargado 200 and back → auxiliar 200; POST `/objetos-perdidos` (2026-06-01 and
    2026-10-01) 201, GET 200, DELETE 204. Browser as Jefe: objetos tabs "En custodia 1 · Vencidos
    +90 días 1", the old one shows "Vencido" with Entregar; `/auxiliares` switch on/off works;
    `/atenciones` ticket modal renders, clone 2× into LAB-02 created 2 rows; 0 console errors.
    The print dialog itself was not exercised. No Python touched (no pytest/ruff needed); no
    Angular spec files exist (test-first exception). GitNexus index is for another checkout.
- 2026-10-09: G3 done (route: delegated, one writer; trigger: 2+ non-trivial files across
  migration, API and Angular). Commits `6c77a69` feat(asignacion): add turno and medio to
  atenciones and a lab dashboard, `310b944` feat(horarios): add turno and medio to attentions
  and a lab dashboard.
  - Migration `0024_horarios_turno_medio` (inline `_run_sql`, with downgrade):
    `atenciones.turno` (M/MD/T/N, NOT NULL after backfill) and `medio_solicitud`
    ('Presencial'|'WhatsApp', default Presencial), CHECK constraints; BEFORE INSERT trigger
    `trg_atenciones_turno` fills a missing turno from the linked `turnos_trabajo`, else from
    `fn_turno_horario_de(creado_en)` (horarios_turno hours in La Paz, latest started turno
    still running, fallback N: same rule as fn_dashboard_detalle `tickets_por_turno`). It also
    covers the RPC inserts (reparaciones, cambio de estado). Backfill disables
    `trg_atenciones_actualizado` so `actualizado_en` is untouched. New
    `fn_dashboard_laboratorios(desde, hasta, turno, ambiente_id)` (permission
    fn_puede_gestionar_auxiliares like the other dashboards): kpis (total, lab_top, turno_top,
    auxiliares_activos), por_lab (top_tipo, top_turno), por_tipo, por_turno (all 4, shift
    order), por_medio, por_mes (January .. month of `hasta`).
  - API: `AtencionIn` + `turno`/`medio_solicitud` (values checked by the DB → 422);
    GET `/atenciones?turno=&medio_solicitud=`; GET `/dashboard/laboratorios` (declared before
    `/{dashboard}`; `FiltroLaboratorios` = range + Literal turno + ambiente_id).
  - Angular: atenciones list filters Turno and Medio, card chips (turno, WhatsApp), form
    selects (turno "Automático (turno abierto u hora)" on new, hidden for a new correctivo
    which goes through the RPC), CSV columns, printable ticket rows, clone keeps the medio.
    New page `/dashboard-laboratorios` ("Labs por turno" menu item, guard
    exigirGestionAuxiliares, link from Desempeño): container `dashboard-laboratorios`
    (mes, turno, lab filters, CSV of the per-lab table) + presentational
    `dashboard-laboratorios-vista` (KPIs, per-lab table, year trend with
    `app-grafico-lineas`, bars by lab/turno/category with `app-grafico-barras`, medio bars).
    No new chart dependency.
  - Semantics chosen: Django turnos mañana/mediodia/tarde/noche → horarios M/MD/T/N; Django
    "categoría" (LabCategoria) → horarios `tipo`; Django "auxiliares activos" (distinct
    auxiliar_nombre) → distinct `auxiliar_id`; Django allowed a null turno, horarios always
    derives one; permission is the horarios dashboard one (admin/encargado), not Django's
    `_puede_reportes`.
  - Tests: RED 13 failed / 58 passed (`test_asignacion_operacion.py` +
    `test_asignacion_dashboards.py`), GREEN 71 passed; all `tests/test_asignacion*` 169 passed;
    full suite 90 failed / 248 passed / 39 errors (same failure counts as baseline, seed users).
    Host ruff check + format clean on the 8 touched Python files.
  - Migration: test DB and UPDS DB upgrade → 0024, downgrade -1 → 0023, upgrade → 0024 (head).
  - Checks: horarios image build → "Application bundle generation complete", no errors. Smoke
    on :4213: paul POST 2 atenciones 201 (explicit T/WhatsApp; the other defaulted to T at
    17:59 La Paz, medio Presencial), GET filter turno=T&medio=WhatsApp → only the first,
    turno "mañana" → 422, paul `/dashboard/laboratorios` 403, Jefe (minted) 200 (kpis total 2,
    LAB-01, turno T) and 200 with turno+lab filter, DELETE 204, 0 smoke rows left. Browser as
    Jefe: `/dashboard-laboratorios` renders, "Labs por turno" in the menu, 0 console errors.
    No Angular spec files exist (test-first exception for the Angular part).
  - Left out: Django `fuera_por_turno`/`fuera_por_auxiliar` (no "fuera de turno" flag in
    horarios), the 10 "recientes" rows of the Django dashboard, and Django's raw-rows CSV export
    for labs (the atenciones list CSV now carries turno and medio). GitNexus index is for another
    checkout (detect_changes not run).
