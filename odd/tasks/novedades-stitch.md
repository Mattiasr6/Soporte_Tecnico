# Novedades Starbucks (Stitch → Django)

Fuente: Stitch proyecto `Soporte V2 - Starbucks` (design system `Starbucks V2`, `#00754a`),
pantalla `Novedades del Turno - SOPORTE UPDS` (`screens/b1824f480c3a4259849ff54374613ce2`).
HTML origen: `/tmp/novedades_stitch.html`.

## Alcance
- Solo `frontend-django/templates/atenciones/novedades.html`. Sin cambios en `views_lab.py`.
- Se conserva 100% la lógica: tabs `?tab=`, POST crear/devolver/validar/rechazar/purgar,
  filtros `f_turno`, fotos vía `novedad_foto`, CSRF, composer JS por `TAB`.
- Tailwind/FontAwesome del mock → CSS propio con scope `.nov2` + iconify (lo que ya carga `base.html`).

## Tasks
- [x] Generar pantalla en Stitch con design system Starbucks V2
- [x] Portar layout a `novedades.html` (tabs con conteos, composer 3 tarjetas, muro cards, kanban)
- [x] Validar sintaxis template (`TEMPLATE OK` en `soporte-dev_web_1`; volumen montado → cambio ya vivo)
- [ ] Revisión visual en dev con sesión (`/auxiliares/novedades/` redirige a login sin sesión)
