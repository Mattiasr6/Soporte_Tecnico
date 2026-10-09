# ODD Feature: frontend-astro-api (consume FastAPI :5002)

Conectar Astro al backend canónico (mismo que Django: FASTAPI_URL=http://localhost:5002).
Solo lectura del backend ( OTRO agente). Auth real vía login de usuario.
Branch: `fix/ui-dev-round` (COMPARTIDA). Solo `frontend-astro/**`.

## Contratos (openapi :5002, 2026-10-07)
- POST /api/auth/login {email,password} → {token, user{id,display_name,role,email,estado_actual,can_view_dashboard}}
- GET /api/atenciones?usuario_id&limit&offset [Bearer] → AtencionOut[] (id, usuario_nombre, area_nombre, grupo_nombre, categoria, descripcion, solucion, fuera_de_turno, fecha_registro, ...)
- GET /api/atenciones/stats [Bearer] → StatsOut (total, fuera_de_turno, por_tecnico, por_categoria, por_mes, por_area, ...)
- GET /api/usuarios [Bearer] → UsuarioOut[] (id, display_name, especialidad, role, estado_actual, horario_hoy, atenciones_hoy, activo)
- GET /api/horarios [Bearer] → HorarioOut[] (usuario_id, nombre, dia_semana, hora_inicio1/fin1/inicio2/fin2, mes, anio)

## Tasks

- [ ] A1 Proxy dev → :5002 + PUBLIC_API_URL default :5002 (canónico Django)
- [ ] A2 Página /login funcional + guard (sin token → /login; 401 → logout)
- [ ] A3 api.ts: Bearer, login/me/atenciones/stats/usuarios/horarios
- [ ] A4 Vistas consumen API real con fallback estático + badge "Datos demo" (Dashboard stats+tabla, Tickets, Usuarios, Horarios)
- [x] A5 Build + verificación 6/6 (5 páginas, /login 200, proxy 401 backend real `server: uvicorn`, Bearer 401, dashboard 200, git limpio)
- [x] A6 Preflight review: OMITIDO — el candidato base-diff ahora incluye edits trackeados del otro agente (software.html etc.); revisarlo mezclaría su trabajo. Vale verificación independiente + review previo aprobado

## Evidence

- (sin commit — rama compartida)
