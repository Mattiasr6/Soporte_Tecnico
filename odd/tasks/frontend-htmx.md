# ODD Feature: frontend-htmx (Django empresarial paralelo)

Django real (Templates + htmx + Alpine + Tailwind CDN) estilo Starbucks House,
PARALELO a frontend-django (comparar, no reemplazar). Puerto 8131.
Branch: `fix/ui-dev-round` (COMPARTIDA). Solo `frontend-htmx/**` (+ su .gitignore propio).
Backend solo lectura (GETs + POST login). Sin commit.

## Tasks

- [ ] H1 Proyecto Django 6 + .venv propio (ignorado) + settings (port 8131, FASTAPI_URL :5002)
- [ ] H2 Tokens Starbucks + base.html (sidebar 272px, topbar) + htmx/Alpine/Tailwind CDN
- [ ] H3 Login ( FastAPI login → JWT en sesión) + logout + guard
- [ ] H4 Atenciones: tabla densa + filtros htmx (partial) + paginación
- [ ] H5 Usuarios: directorio + búsqueda htmx
- [x] H6 README + verify 7/7 (check, login 200, wrong-creds backend error, guards 302, tokens, git limpio)
- [x] H7 Review: DECLINED candidate-scoped (high risk: manage.py corre procesos — correcto para prototipo local, jamás exponer). Vale verificación independiente
- [x] H8 Polish cálido verificado (Tailwind config inline + gold accents + drawer/dropdown Alpine + spinners htmx + login split + empty states). Sin vistas nuevas, sin tocar backend
- [ ] H9 Iconos Iconify MDI (cero emojis en todo frontend-htmx)
- [ ] H10 Sidebar colapsable a rail (Alpine, persistido)
- [ ] H11 Paridad atenciones oficial: filtro mes, cards móvil, modal detalle+edición (PUT), nueva (POST batch), jerarquía 3 niveles, flash
- [x] H12 Paridad usuarios (rol/activo/reset/crear) + horarios edición (mes nav + guardar lote + limpiar) — verify 6/6. Nota: POST sin slash → RuntimeError APPEND_SLASH (idéntico al Django oficial, solo URLs malformadas)
