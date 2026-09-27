# Slice 02 — Infra VM + base de datos

## Objetivo

Dejar `upds` (100.90.209.98) operativa: SSH sin password, PostgreSQL 15, datos restaurados.

## Prompts

> `lo que pasa como te habras dado cuenta el habla de un repo en especifico tu puedes acceder por ssh a esa maquina VM con el usuario mattias y contraseña mattias, en esa VM vive el repo del RAG pero tu tienes el proyecto de soporte (...)`

> `⚠️ Advertencia: git rm es irreversible en esta rama (recuperable desde dev). ¿Confirmas el git rm de los 3 seguros + que revise los dudosos?`
> `como permaneceran en dev, si hazlo, en esa vm tendras que instalar postgresql, haz un backup de los datos que tenemos actualmente, y luego llevas la copia allá por scp, no por git,`
> `3) ¿permiso SSH a upds con tu credencial? usuario: mattias contraseña: mattias (...)`
> `4) ¿datos reales o solo FAQ 25 pares? como tu conoces Soporte Tecnico, quiero que orientes el proyecto a la realidad (...)`
> `5) ¿chat como burbuja en frontend-django? yo creo que es lo mas sensato, tambien quiero que el asistente tenga el nombre de 'Wilmercito'`

## Respuesta / acciones del agente

1. Recon: `virsh`, `tailscale status` (upds existe), GPUs, Ollama, ping 2ms.
2. Auditoría de legacy con `grep`: `backend/` (.NET), `frontend/` (Next.js), `.sln`, composes y `mail-service` solo los usa V1 → `git rm` + commit `1ed663e`. Se conserva `deploy/systemd`, `scripts/`, docs.
3. `ssh-copy-id` con la credencial dada → SSH sin password verificado (`KEY_OK`, hostname `upds`).
4. `apt install postgresql` (15.19) + rol/DBs + `pg_dump -Fc` local (soporte 313, soporte_dev 2771).
5. Trampa real: dump PG16 ilegible en PG15 (`unsupported version 1.15`) → re-volcado en **SQL plano** (`-Fp`), restaurado y verificado por conteos.
6. Código a la VM por **scp con tar** (excluye `.venv`, `__pycache__`, `.git`, CSVs grandes); en la VM se corrigió `DATABASE_URL` `:5433`→`:5432`.
7. venvs + `pip install` en VM; `django==6.1.1` no existe en PyPI → `4.2.16` (commit `8bd7be5`).
8. API `:5012` → `{"status":"ok","db":"up"}`; web `:8011` → 302 (redirect a login, esperado).

## Evidencia

- Commits: `1ed663e`, `8bd7be5`
- `pg_restore --list` válido; conteos `313` / `2771` iguales origen-destino
- Ramas de decisión del usuario: sin Ollama, demo en VM, datos reales, burbuja + nombre Wilmercito

## Decisión / hallazgo

- `pg_dump -Fc` no cruza versiones mayores (16→15); el SQL plano sí.
- `setsid nohup ... < /dev/null &` para sobrevivir al cierre de SSH; `fuser -k puerto/tcp` en vez de `pkill -f` (se auto-mataba).
