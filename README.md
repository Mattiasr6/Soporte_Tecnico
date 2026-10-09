# Sistema de Soporte Técnico + Auxiliares

https://github.com/Mattiasr6/Soporte_Tecnico — https://soporte.visita-samaipata.me

Dos paneles, una base:

- **Soporte**: tickets de técnicos (CRUD, batch, reportes, dashboard, jerarquía, horarios, usuarios, sugerencias) + asistente IA local «Wilmercito».
- **Auxiliares (labs)**: registros de laboratorio, nómina con encargados, turnos y horarios con drag&drop, dashboard, reportes + CSV.

## Roles

| Rol | Ve | Puede |
|---|---|---|
| Jefe | todo | todo (usuarios, roles, claves, equipo, anuncios) |
| Encargado | panel Auxiliares + dashboard/reportes labs | nómina y horarios, sus atenciones |
| Técnico | panel Soporte | sus atenciones |
| Auxiliar | panel Auxiliares (lectura equipo/horarios) | sus atenciones |
| Decano | panel Soporte (como Técnico, sin privilegios) | nada propio: permisos en Soporte pendientes de definir; en Horarios = `decano` |
| Invitado | panel Soporte (como Técnico, sin privilegios) | nada propio: permisos en Soporte pendientes de definir; en Horarios = `invitado` (sin acceso) |

## Ambientes

| | Web | API | PG |
|---|---|---|---|
| Prod (Podman) | :8001 | 127.0.0.1:5002 | :5433 |
| Dev (Podman) | :8011 | 127.0.0.1:5012 | :5434 |

Dev monta el código en vivo (`Soporte_Tecnico2`): editar → recargar. Clave demo: `demo1234`.

## Flujo de trabajo

Rama/PR → CI (lint+tests, afuera) → merge a `main` → Deploy (con aprobación): backup + build + migrate + verify.

Nómina y horarios reales viven en volumen `appdata-prod` + `~/backups-actions/` — jamás en git (`backend-fastapi/data/*.json` ignorado).

## Estructura

```
backend-fastapi/app/
  routers/      atenciones.py auth.py ia.py usuarios.py jerarquia.py areas.py horarios.py laboratorios.py announcements.py
  services/     ia_retrieval.py estados.py horarios.py
  models/       atencion.py usuario.py lab*.py feedback_ia.py ...
frontend-django/
  atenciones/   views.py views_lab.py context_processors.py (sistema SOPORTE/AUXILIARES)
  templates/atenciones/  + static/css/tokens.css + static/js/
deploy/podman/  prod.compose.yml dev.compose.yml Caddyfile .env.*.example
.github/workflows/  ci.yml deploy-prod.yml migrate-prod.yml duckdns-sync.yml
```

## Notas

- Django 4.2.16 · FastAPI · Postgres 16 · Podman (red host en prod).
- Público vía túnel Cloudflare (sin puertos abiertos ni IP fija).
- `tests/conftest.py` exige DB terminada en `_test`.
