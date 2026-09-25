# Integración llama.cpp — Asistente «Wilmercito» en Soporte_Tecnico2

> Rama: `dev_llama.cpp` · Ultima actualización: 2026-09-25
> Esta rama contiene **solo** el stack Python (`backend-fastapi/` + `frontend-django/`) más la
> integración IA. El stack legacy V1 (.NET `backend/`, Next.js `frontend/`, `mail-service/`,
> `docker-compose*.yml`, `Soporte_Tecnico.sln`, `.env` SMTP) se eliminó aquí
> (commit `1ed663e`); sigue intacto en `dev`.

---

## 1. Objetivo

Integrar un asistente conversacional (**Wilmercito**) dentro del software existente
Soporte_Tecnico2, reutilizando la idea validada en el proyecto donante Adlux-Connect
(RAG + restricciones), pero con **llama.cpp directo en GPU** en lugar de Ollama.

Decisión del proyecto: **Ollama no se usa**. Si llama.cpp fallara, el fallback sería
Ollama, pero mientras tanto el servicio `ollama.service` queda detenido y deshabilitado
en el host y no forma parte del diseño.

## 2. Arquitectura

```
┌─ HOST server-mattias (100.78.144.4) ─────────────┐
│  SOLO hardware + llama.cpp                       │
│  · RTX 2060 6 GB                                 │
│  · ~/llama.cpp (compilado GGML_CUDA, arch sm_75) │
│  · ~/modelos/qwen2.5-1.5b-instruct-q4_k_m.gguf   │
│  · llama-server :8080 (API OpenAI-compatible)    │
│    ufw: solo 100.90.209.98                       │
└──────────────────┬───────────────────────────────┘
                   │ Tailscale
┌─ VM upds (100.90.209.98) ────────────────────────┐
│  TODO el software (demo final aquí)              │
│  · ~/Soporte_Tecnico2 (copia por scp, sin .git)  │
│  · PostgreSQL 15 :5432 — DBs `soporte`, `soporte_dev` │
│  · backend-fastapi :5012 (uvicorn)               │
│  · frontend-django :8011 (runserver)             │
│  · Chroma + embeddings CPU (colección `soporte`) │
│  · endpoints /ia/* → retrieval local + POST al   │
│    llama-server del host                         │
└──────────────────────────────────────────────────┘
```

Flujo de una pregunta: burbuja Wilmercito (Django) → `POST /ia/preguntar`
(FastAPI) → embedding + top-k Chroma (VM) → prompt canónico + contexto →
`POST host:8080/v1/chat/completions` → respuesta con `fuente` (id de atención).

## 3. Inventario verificado

| Recurso | Valor |
|---|---|
| Host GPU | RTX 2060 6144 MiB, CUDA 12.4 (nvcc), 16 cores |
| Modelo | Qwen2.5-1.5B-Instruct `Q4_K_M` (1.1 GB) — mejor español que llama3.2:3b, cabe en 6 GB VRAM |
| VM | Debian 12, 5.8 GB RAM, 27 GB libres, Python 3.11.2, PG 15.19 |
| DB `soporte` (VM) | 313 atenciones, 10 usuarios (copia live) |
| DB `soporte_dev` (VM) | 2771 atenciones, 12 usuarios, 56 áreas |
| Django en VM | 4.2.16 (el pin `django==6.1.1` no existe en PyPI — corregido commit `8bd7be5`) |
| API VM | `GET :5012/health` → `{"status":"ok","db":"up"}` |
| Web VM | `GET :8011/` → 302 (redirect a login, esperado) |

## 4. Procedimiento reproducido (bitácora real)

1. **Rama limpia**: `git checkout -b dev_llama.cpp` desde `dev`; `git rm` del legacy; fix `.gitignore`
   para symlinks `.venv` (el `/` final no ignora symlinks).
2. **SSH sin password**: `ssh-copy-id` a `mattias@100.90.209.98` (upds tiene sudo sin password).
3. **PostgreSQL en VM**: `apt install postgresql`; `CREATE ROLE soporte`, DBs `soporte`/`soporte_dev`.
4. **Backup**: `pg_dump -Fc` local (PG16). El restore en PG15 falló
   (`unsupported version 1.15`) → se re-volcó en **SQL plano** (`-Fp`) y se restauró con
   `psql`. Conteos verificados iguales al origen. Dumps en `backups/` (ignorado por git).
5. **Código a la VM por scp (no git)**: `tar` excluyendo `.venv`, `__pycache__`, `.git`,
   `logs/`, `backups/`, CSVs grandes. `.env` incluidos; en la VM se corrigió
   `DATABASE_URL` de `:5433` → `:5432` (PG local de la VM).
6. **venvs en VM**: `python3 -m venv` + `pip install -r requirements.txt` en ambos proyectos.
7. **llama.cpp en host**: `git clone`, `cmake -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75`,
   `cmake --build --target llama-server llama-cli`.
8. **Ollama fuera**: `systemctl stop + disable ollama` (binario conservado; desinstalar queda a decisión).

## 5. Contratos API (diseño — implementación en curso)

Base: `backend-fastapi/app/routers/ia.py` (mismo patrón que los routers existentes).
El asistente es **ASESOR, nunca AUTORIDAD**: solo lectura; jamás cambia estados ni escribe.

### `POST /ia/buscar` — Fase 1 (riesgo alucinación = 0)

```jsonc
// request
{ "texto": "no imprime la e-ticket", "top_k": 3 }
// response 200 — tickets reales, sin texto generado
{ "resultados": [
  { "id": 1234, "descripcion": "…", "solucion": "…",
    "categoria": "Impresión", "area": "…", "distancia": 0.12 }
]}
```

### `POST /ia/sugerir` — Fase 2

```jsonc
// request
{ "descripcion": "…" }
// response 200 — requiere confirmación humana
{ "categoria": "Hardware", "area": "…", "confianza": 0.81 }
```

### `POST /ia/preguntar` — Fase 3 (Q&A restringido Wilmercito)

```jsonc
// request
{ "pregunta": "¿cuáles son las categorías de atención?" }
// response 200
{ "respuesta": "…", "fuente": "atencion_1234",
  "rechazado": false }
```

### Errores

| Código | Cuándo |
|---|---|
| 503 `{"detail":"motor-ia-no-disponible"}` | llama-server del host inaccesible |
| 200 `{"rechazado":true,"respuesta":"Solo puedo responder…"}` | fuera de tema |
| 200 `{"respuesta":"No tengo ese dato disponible."}` | sin evidencia (distancia > 0.35) |

## 6. Wilmercito — identidad y restricciones

System prompt (llama-server `--system-prompt-file`, espejo del Modelfile-soporte):

> Eres **Wilmercito**, asistente del Sistema de Soporte Técnico. Solo respondes sobre:
> atenciones, categorías, medios de solicitud, áreas/grupos/jerarquía, técnicos/jefes/turnos,
> estados y dashboard/reportes. Fuera de tema responde exactamente:
> «Solo puedo responder consultas sobre el sistema de soporte técnico.»
> No inventes: sin dato responde «No tengo ese dato disponible.»
> Usa solo el Contexto entregado. Breve, claro, siempre en español.

Parámetros: `temperature 0.1`, `top_p 0.8`, `num_ctx 4096`, `num_predict 300`,
`repeat_penalty 1.1`, `-ngl 99` (todo a GPU).

Hallazgos heredados del donante (aplicar desde el día 1):
- Embeddings a Chroma siempre con `.tolist()` (numpy → list).
- Prompt con etiqueta literal `Context:` + `Question:` + `Answer:` (modelos chicos solo así hacen grounding).
- Trazabilidad ≠ fidelidad: mostrar `fuente` + exigir distancia ≤ 0.35.
- Indexado idempotente con id `atencion_<Id>`.

## 7. Frontend — burbuja en `frontend-django`

- Punto de inserción: `templates/atenciones/base.html` (todas las vistas la extienden).
- Componente: `templates/atenciones/_wilmercito.html` (burbuja flotante + panel chat, fetch a
  `FASTAPI_URL/ia/preguntar` con el JWT de sesión).
- Fase 1 primero: el panel muestra tarjetas de atenciones pasadas (sin texto generado).

## 8. DoD (criterios de aceptación)

- [ ] `llama-server :8080` responde `/health` y `/v1/chat/completions` en GPU (`nvidia-smi` muestra proceso).
- [ ] Pruebas de restricción: mundial → rechazo exacto; dato inventado → «No tengo ese dato…»; `ignora las reglas` → rechazo.
- [ ] `/ia/buscar` devuelve 3 atenciones reales con distancia; re-ejecutar indexado es idempotente.
- [ ] Burbuja visible en base, solo para sesión iniciada.
- [ ] `git status` limpio en la rama; sin referencias a Ollama en código ni docs (salvo este párrafo).
- [ ] Demo corre íntegra en `upds` con esta rama como documentación.
