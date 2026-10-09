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

- D1 Labs/PCs: `Laboratorios`/`LabPcs` vs `horarios.ambientes`/`ambiente_pcs` (Software follows).
- D2 Lab attentions: `LabAtenciones` vs `horarios.atenciones`.
- D3 Shifts/auxiliares: JSON files + `mañana/mediodia/tarde/noche` vs `horarios.perfiles` + `M/MD/T/N`.
- D4 Novedades: `Novedades` vs `horarios.reportes_turno` + `objetos_perdidos`.
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
- [ ] M3 Auditoría (read-only, Jefe): `/api/auditoria`.
- [ ] M4 Soporte attentions list + ticket (needs D5).
- [ ] Later areas (dashboards, reports, jerarquía, IA, labs, auxiliares, novedades) are added
  as tasks once their blocking decision is answered.

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
