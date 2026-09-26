---
title: "Turnos GPU + jobs nocturnos (serve de día, entrena de noche)"
status: "approved"  # draft | approved | rejected
version: "1.0"
priority: "alta"
estimated_effort: "2 sesiones"
dependencies: ["llama-server.service en host", "VM upds con PG15", "docs/fine-tuning-lora.md"]
---

### Historia de usuario

> **Como** jefe del equipo, **quiero** que la GPU sirva de día y mejore el modelo de noche
> **para** que Wilmercito aprenda solo sin interrumpir el servicio.

### Objetivo

Ventana nocturna 01:00–05:00: jobs de mejora + entrenamiento; de día, inferencia.

---

## Stack Tecnológico (OBLIGATORIO)

| Capa | Tecnología | Versión | Notas |
|------|-----------|---------|-------|
| GPU | RTX 2060 6 GB, CUDA 12.4 | host | turnos por systemd timers |
| Serve (día 05:00–01:00) | llama-server build propio | :8081 | GGUF activo |
| Dataset | `scripts/ft/build_dataset.py` | rama | tickets + KB + feedback + rechazos |
| Train (noche) | Unsloth QLoRA Qwen2.5-3B | `~/ft-wilmercito/` | r=16, batch 2, 1–2 epochs |
| Eval | `POST /ia/evaluar` + ragas faithfulness | — | regresión = aborta despliegue |
| Orquestación | systemd timers host + VM | — | sin cron (no existe en host) |

## Arquitectura

### Diagrama de componentes (textual)

```
[timer 01:00] --> stop llama-server --> [job: reindex] --> [job: evaluar+alerta]
   --> [job: build_dataset] --> [job: train_qlora] --> [job: eval adapter]
   --> [si pasa: merge+GGUF] -- [timer 05:00] --> start llama-server (nuevo GGUF)
```

### Mapa de archivos

```
# Archivos a crear:
scripts/ft/build_dataset.py      # DB+KB+feedback -> data/ft_train.jsonl (formato messages)
scripts/ft/validate_dataset.py   # JSONL válido, roles, duplicados, balance de clases
scripts/ft/nightly.sh            # orquesta la ventana (stop/jobs/start con lock)
docs/specs/turnos-gpu.md         # esta spec

# Infra (fuera de la rama, documentada):
/etc/systemd/system/ft-nightly.{service,timer}   # host 01:00
/etc/systemd/system/llama-server.service         # ya existe; el job lo para/arranca
```

## Contratos de Datos

### Dataset (`data/ft_train.jsonl`, formato messages)

```json
{"messages": [{"role": "system", "content": "<WILMERCITO_SYSTEM>"},
              {"role": "user", "content": "¿cuáles son las categorías?"},
              {"role": "assistant", "content": "Las 8 categorías…"}]}
```

Clases obligatorias: `tickets` (2771), `kb` (curada), `feedback` (promovido),
`rechazo` (~40 sintéticos: mundial, jailbreaks), `identidad` (Wilmercito).

### Job evaluar+alerta

```python
# POST /ia/evaluar (jefe) -> {"n": 10, "con_fuente": 10, "filas": [...]}
# Alerta si: con_fuente < 9, o p95 (LogIA 24h) > 30000ms, o rechazos/hora > 5
# Destino alerta (v1): archivo ~/ft-wilmercito/ALERTAS.md (el jefe lo ve en /asistente)
```

## Flujo Principal — noche estándar

1. 01:00 timer para `llama-server` (API responde 503, documentado como degradado)
2. Reindex Chroma (cambios del día) vía `POST /api/ia/reindexar`
3. `/ia/evaluar` → si regresión, escribe ALERTAS.md y **aborta** (no entrena sobre datos rotos)
4. `build_dataset.py` + `validate_dataset.py` (falla si JSONL inválido)
5. `train_qlora.py` (Unsloth, ~2–4 h)
6. Eval del adapter contra `data/ft_eval.jsonl`; si pasa → merge + GGUF `wilmercito-3b-AAAAMMDD-q4_k_m.gguf`
7. 05:00 arranca `llama-server` con el GGUF más nuevo que pasó eval (rollback = anterior)

### Flujo Alternativo — sin datos nuevos

1. Si `build_dataset.py` genera 0 pares nuevos → se salta train (solo eval + alerta).

### Flujo de Error

| Condición | Respuesta | Acción |
|-----------|-----------|--------|
| Eval con regresión | aborta noche | ALERTAS.md + mantiene GGUF actual |
| OOM en train | aborta | reintenta con batch 1 a la noche siguiente |
| 05:00 y train sin terminar | mata train | arranca serve (servicio manda) |

## Catálogo de Errores

| Código | Condición | Visible | Log |
|--------|-----------|---------|-----|
| FT-001 | dataset inválido | ALERTAS.md | error |
| FT-002 | regresión en eval | ALERTAS.md + /asistente | error |
| FT-003 | OOM | ALERTAS.md | error |
| FT-004 | serve no arranca 05:00 | systemd failed | error |

## Criterios de Aceptación (Gherkin)

```gherkin
Feature: Turnos GPU

  Scenario: Noche normal sin datos nuevos
    Given timer 01:00 dispara
    When build_dataset da 0 pares nuevos
    Then se salta train y serve arranca 05:00 con el mismo GGUF

  Scenario: Regresión frena despliegue
    Given evaluar con con_fuente < 9
    When corre el job
    Then aborta antes de train y escribe ALERTAS.md
```

## Definition of Done (DoD)

1. [ ] `build_dataset.py` genera JSONL válido desde DB real (tickets+KB+feedback+rechazos)
2. [ ] `validate_dataset.py` rechaza JSONL roto (test con fixture mala)
3. [ ] Noche simulada de día (comando manual) corre stop→jobs→start sin errores
4. [ ] Timers instalados y documentados; rollback probado (GGUF anterior arranca)
5. [ ] Rama limpia

## Orden de Implementación

1. **Paso 1:** `build_dataset.py` + `validate_dataset.py` — `scripts/ft/`
2. **Paso 2:** `nightly.sh` + corrida manual diurna — host
3. **Paso 3:** timers + ALERTAS.md visible en `/asistente` — host + Django
4. **Paso 4:** `train_qlora.py` (Unsloth) primera noche real — `~/ft-wilmercito/`

## Lo que NO está en alcance (explícito)

- ❌ Entrenar de día (la VRAM no da para servir + entrenar)
- ❌ Auto-despliegue sin pasar eval (siempre con gate)
- ❌ Datasets con datos personales fuera del esquema (solo tickets/KB/feedback)
