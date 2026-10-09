# ODD Feature: frontend-astro

Stack: Astro 5 + Vue islands + Tailwind + PrimeVue. Consume `backend-fastapi` vía proxy.
Branch: `fix/ui-dev-round` (COMPARTIDA con otro agente — NO crear ramas).
Constraint: NO tocar `backend-fastapi/` ni `frontend-django/`; todo el trabajo vive dentro de `frontend-astro/`.

Referencias: Engram personal #52 (infra MCP), #53 (plan Astro + DS Stitch emerald/Jakarta).
Diseños Stitch: proyecto 3964285493767268898; HTMLs en `Soporte_Design/design-reference/` (port pages = fase posterior, fuera de scope).

## Tasks

- [x] T1 Scaffold Astro (template minimal, TS strict) en `frontend-astro/`
- [x] T2 Integraciones Vue + Tailwind v4 (@tailwindcss/vite 4.3.3) + PrimeVue 4.5.5/Aura + tokens emerald/Jakarta stub
- [x] T3 Dev server puerto 4321 + proxy `/api` → `http://localhost:8000` + env `PUBLIC_API_URL`
- [x] T4 Layout base (sidebar 240px, tokens semánticos, Heroicons) + isla DemoTable.vue hidratada
- [x] T5 Cliente API tipado (`src/lib/api.ts`; `gen:api` sin spec: backend devuelve redirect login en /openapi.json)
- [x] T6 `npm run build` OK + smoke test dev server (verify agent 4/4 pass)
- [x] Review nativo: lineage review-48d0586efb12f7d7 APPROVED + acknowledged (lente reliability, 3 warnings informativos en api.ts)
- [ ] T7 Work-unit commit OMITIDO: rama compartida fix/ui-dev-round — commit queda a decisión del usuario

## Evidence

- (commits al cerrar cada tarea)
