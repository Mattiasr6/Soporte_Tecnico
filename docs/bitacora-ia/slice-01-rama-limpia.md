# Slice 01 — Rama limpia

## Objetivo

Verificar que `dev` estuviera commiteada y crear `dev_llama.cpp` para el trabajo de IA.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `Necesito que verifiques que la rama dev tenga todo commiteado. Ahora trabajaremos en una nueva rama llamada 'dev_llama.cpp'.`

> `¿Ya hiciste el recovery con meta_learner?`

## Respuesta / acciones del agente

1. `git status` en `dev`: encontró 3 pendientes — `backend-fastapi/.venv`, `frontend-django/.venv` (untracked) y `docs/HANDOFF-ollama-modelfile.md`.
2. Hallazgo: los `.venv` son **symlinks**, y el `/` final del `.gitignore` no ignora symlinks.
   Fix: agregadas las rutas sin `/` final. Verificado con `git check-ignore`.
3. Commit en `dev`: `4203e9d chore(dev): ignora symlinks .venv y agrega HANDOFF ollama-modelfile`.
4. Creada `dev_llama.cpp` desde `dev`, limpia.
5. Ante la pregunta del recovery: el agente admitió que no lo había hecho, cargó el skill
   `meta-learner` e hizo `meta-learner_recover(last: 3)` → 2 compacts (rescate Adlux-Connect,
   corte S10). De ahí salió el contexto del Modelfile y `faq_soporte.json`.

## Evidencia

- Commits: `4203e9d`
- Comandos: `git status --porcelain=v1 -b`, `git check-ignore -v`, `git checkout -b dev_llama.cpp`
- `meta-learner_recover(last: 3)` → `compact_1790352461819`, `compact_1790168885929`

## Decisión / hallazgo

- Los symlinks no se ignoran con `/` final en `.gitignore` (lección reutilizable).
- HANDOFF commiteado en `dev` como puente entre sesiones.
