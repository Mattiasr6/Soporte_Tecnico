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
- D5 Angular role model: `ROLE_MAP` sends Tecnico → invitado, so technicians have no real role
  in Angular (needed before the Soporte area).

## Tasks

- [x] M0 Groundwork: Angular client for non-`/asignacion` FastAPI routes (second base in
  `core/`), plus a "Mi cuenta" entry in the layout menu. Route: delegated (multi-file).
- [x] M1 Perfil: view/edit display name and change password (re-login after change, as
  Django `perfil_guardar_vista`). Uses `/api/usuarios/me`. Route: delegated with M0.
- [x] M2 Notas personales: GET/PUT `/api/usuarios/notas`. Route: delegated with M0.
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
  - Note: Soporte `Tecnico` users map to Angular `invitado` (D5), so they only see `/espera`
    and cannot reach Mi cuenta in Angular yet.
  - Checks: horarios image build → "Application bundle generation complete", no errors;
    login as paul → GET `/api/usuarios/me` 200, GET `/api/usuarios/notas` 200; POST
    `/api/auth/password` with a wrong current password → 401 (confirms the exemption is
    needed; password not changed); `/cuenta/perfil` and `/cuenta/notas` → 200 (SPA fallback);
    `cuenta/perfil` present in the served `main-*.js`. No spec files exist (test-first
    exception); no browser click-through was done.
