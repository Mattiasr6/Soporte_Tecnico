# Slice 14 — Producción (P0 + merge + deploy)

## Objetivo

Dejar el sistema presentable y operable: backups, servicios, credenciales, tests, merge, deploy.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `Dime qué continúa para que este sistema realmente sea considerado 'funcional' (...) que valga la pena que esté en producción.`
> `(Hoy nadie se entera) Haz primero P0 y luego (...)`
> `¿Ahora qué procede para continuar con el deploy y merge paso a paso?` → `Sí, hazlo.`
> `¿Me aseguras que lo que tenemos en dev no se perderá? ¿O necesitas que abra OpenCode desde la carpeta Soporte_Tecnico-python (...)?`

## Respuesta / acciones del agente

1. P0 ejecutado: backups diarios (cron VM + timer host, restore probado 2771), `llama-server.service` con `Restart=always` (kill -9 verificado), credenciales demo rotadas + `JWT_SECRET`, 9 tests IA (encontraron 2 bugs reales).
2. Merge `dev_llama.cpp` → `python-experiment` (`69f849d`, 0 conflictos) con tag de respaldo; `dev` intacta. Garantía explicada: merge solo mueve el puntero destino.
3. Deploy en vivo: venv312 (el venv era py3.14 sin pip y sin torch posible), LLAMA env, migrate 0009, Wilmercito id 11, units a `.venv312`, índice 389, evaluar 9/10 (el décimo: expectativa sobre-ajustada, respuesta válida).
4. Handoff entre directorios vía Engram ("ecram"): memoria con checklist; el otro agente la leyó OK.
5. Búsqueda exhaustiva en paralelo (3 agentes explore) + spec Fase A aprobada con DoD verde.

## Evidencia

- Commits `7c7fed5`, `69f849d`; memorias Engram id 1–3 con veredictos
- `alembic current` → `0009_ia_observabilidad (head)` en prod

## Decisión / hallazgo

- Producir = backups + servicios que resucitan + credenciales + tests + migración verificada, en ese orden.
