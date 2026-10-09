# ODD Feature: frontend-astro-vistas-a (Tickets, Usuarios, Horarios)

3 vistas nuevas en lenguaje Dark Glass + refactor AppShell compartido + routing Astro.
Branch: `fix/ui-dev-round` (COMPARTIDA — NO crear ramas).
Constraint: solo `frontend-astro/**`. Sin referencia Stitch (no existen) — mismo lenguaje que Dashboard.

## Tasks

- [ ] V1 Refactor: `AppShell.vue` (sidebar+topbar+footer) extraído de Dashboard.vue; nav con rutas reales y active state
- [ ] V2 `src/pages/tickets.astro` + `TicketsBoard.vue`: kanban por estado (Pendiente/Diagnóstico/Resuelto) con badges prioridad, modal detalle, mover entre columnas
- [ ] V3 `src/pages/usuarios.astro` + `UsuariosTable.vue`: directorio (avatar iniciales, rol, nivel, sede, contacto, estado), búsqueda, modal nuevo usuario
- [ ] V4 `src/pages/horarios.astro` + `HorariosGrid.vue`: grilla semanal técnicos×días (M/T/N), filtro sede, highlight hoy
- [ ] V5 Sidebar links → rutas reales (/tickets, /usuarios, /horarios); resto # placeholders
- [x] V6 `npm run build` OK + smoke (verify agent 4/4: 4 páginas, 200 + markers, todayIdx dinámico, git limpio)
- [x] V7 Review nativo: lineage review-61341daf81b7cb7f APPROVED + acknowledged (reliability, 3 warnings informativos: api.ts:20, Dashboard.vue:350, UsuariosTable.vue:150)

## Evidence

- (sin commit — rama compartida)
