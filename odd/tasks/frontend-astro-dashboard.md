# ODD Feature: frontend-astro-dashboard (Dark Glass)

Port fiel de `stitch-variant-2.html` (Stitch Dark Glassmorphic) a Vue, con interactividad real.
Branch: `fix/ui-dev-round` (COMPARTIDA — NO crear ramas).
Constraint: solo `frontend-astro/**`. Referencia solo-lectura: `/home/mattias/Proyectos/Soporte_Design/design-reference/stitch-variant-2.html`.

## Tasks

- [ ] D1 Tokens dark glass en `tokens.css` (bg #0b1117, card slate-900/60, emerald #10b981/#059669) + font Plus Jakarta Sans + Material Symbols
- [ ] D2 `src/data/atenciones.ts`: 10 tickets (5 Stitch + 5 nuevos realistas UPDS), técnicos, categorías
- [ ] D3 `Dashboard.vue` (isla raíz): sidebar glass + topbar + 4 KPIs + bento widgets + footer
- [ ] D4 Tabla densa funcional: búsqueda, filtros (categoría/técnico/régimen), chips activos, sort, paginación, export CSV real, reset
- [ ] D5 Modales PrimeVue: detalle ticket (ver) + nueva atención (formulario funcional + Toast)
- [ ] D6 Avatares = iniciales (sin imágenes externas), responsive con drawer móvil
- [x] D7 `npm run build` OK + smoke :4321 (verify agent 4/4: build 0, 200 + 6/6 markers, DemoTable gone, git clean)
- [x] D8 Review nativo: DECLINED para este candidato (consent-binding expirado, sin lineage) — vale verificación independiente (D7) según plan risk-gated; reintentable con START fresco si el usuario lo pide

## Evidence

- (commits solo si el usuario los pide — rama compartida)
