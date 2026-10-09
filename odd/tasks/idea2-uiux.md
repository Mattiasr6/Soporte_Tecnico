# ODD Feature: idea2-uiux ( отвечаю batch 1, solo copia local)

Mejoras IU/UX profesionales sobre `frontend-django-idea2/original/` (corre :8111).
NO tocar `frontend-django/` original. Sin commit (todo gitignored igual).

## Batch 1 (esta tanda)
- [ ] U1 Command palette ⌘K (Alpine: ir a vistas, buscar ticket por ID, acciones)
- [ ] U2 Toasts (mensajes Django → Alpine auto-dismiss apilados)
- [ ] U3 Densidad cómoda/compacta (toggle + localStorage)
- [ ] U4 Atajos teclado (/, n, ? modal ayuda) + skip-link a11y
- [ ] U5 Skeleton rows en cargas htmx/fetch (reemplaza "Cargando…")
- [ ] U6 Export CSV client-side (todas o seleccionadas con checkboxes)
- [ ] U7 Breadcrumbs + headers consistentes + auditoría Iconify (tamaños/alineación)
- [x] U8 Verify 6/6 (login 200+markers, guards 302, 0 emojis, 0 glass/dark, partial OK, original intacto). Pendiente humano: palette completa y CSV con sesión real
- [x] U9 Rediseño visual verificado: sidebar vestido (logo headset Iconify, activo accent+tick oro, toggle segmentado, footer), login split 880px real, tablas (sticky, hover cálido, pills, toolbar, ver-más, cards), fichas KPI, triggers re-homed CSS. Templates parse OK, :8111 200
- [x] U10 Suavizado verificado (Sora+Inter cargan — Inter ni cargaba antes; radios 10/16/full; tablas aireadas; último emoji 🖱️→mdi). Auditoría conexiones: 0 URLs rotas, 0 estáticos faltantes
- [x] U11 COOP off solo en copia (header ausente verificado). Warning era benigno (Django 4.2 default same-origin)
- [x] U12 Modo cine vivo: ruta + nav + sala teatro + selector + refresh 30s + fullscreen. CORRECCIÓN BACKEND: canónico DEV es :5012 (77 paths, pcs existe), NO :5002 (66, stale). Copia apunta :5012 (oficial dev usa api:5012). pcs :5012→401 existe, :5002→404
- [x] U13 Modo demo verificado 5/5 (botón demo → fixtures + cine mock determinista + badge + logout limpio). Entrar sin cuenta y ver TODO

## Backlog (siguiente)
- Vistas guardadas / búsquedas recientes (localStorage)
- Filtros guardados por usuario (POST sugerencias? no — local)
- Timeline actividad en detalle (requiere datos historial)
- Print stylesheet tickets
