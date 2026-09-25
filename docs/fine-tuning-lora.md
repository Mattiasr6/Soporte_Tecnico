# Fine-tuning LoRA de Wilmercito (Qwen2.5-3B) — plan

> Estado: PLANIFICADO (no ejecutado). GPU: RTX 2060 6 GB en `server-mattias`.

## 1. Por qué

El RAG actual razona sobre contexto recuperado, pero el modelo base no "sabe" el
dominio: redacta con estilo genérico y a veces ignora el formato. Un LoRA sobre
tickets reales le enseña el vocabulario (categorías, áreas, medios), el formato
de respuesta (breve, español, cita de fuente) y las restricciones (rechazo exacto).

## 2. Dataset (todo sale del sistema, sin etiquetado manual masivo)

| Fuente | Pares aprox. | Formato |
|---|---|---|
| Atenciones (Descripción → Solución) | 2771 | instrucción: problema + categoría/área; respuesta: solución |
| KB curada + feedback promovido | ~10 y creciendo | pregunta → respuesta exacta |
| Rechazos sintéticos | ~40 | preguntas fuera de tema → rechazo exacto; jailbreaks → rechazo exacto |

Script: `scripts/ft/build_dataset.py` (ya implementado y verificado en VM:
2229 pares válidos desde DB real; ojo: ~500 descripciones duplicadas en tickets,
el builder las filtra) + `scripts/ft/validate_dataset.py`.
Inspiración: `patmakesapps/qwen-qlora-runpod-template` (datasets modulares,
persona, validate/train/test/merge) y `wazih-shourov/Qwen3-8B-Custom-Persona-LoRA`
(identidad propia vía LoRA — como Wilmercito). Eval RAG: `ragas` (faithfulness,
answer relevancy) — ver `docs/specs/turnos-gpu.md`.

## 3. Entrenamiento (Unsloth QLoRA, 6 GB VRAM)

- Base: `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`. QLoRA r=16, alpha=16, batch 2,
  gradient_accumulation 4, 1–2 epochs, lr 2e-4, max_seq 2048.
- Costo estimado: 2–4 h en la 2060. Correr de noche con `llama-server` detenido
  (la VRAM no alcanza para entrenar y servir a la vez).
- Entorno: `~/ft-wilmercito/` (fuera del repo; solo el dataset versionado entra
  a la rama si el docente lo pide, anonimizado).

## 4. Merge + GGUF + despliegue

1. `model.save_pretrained_gguf(..., quantization_method="q4_k_m")` → `~/modelos/wilmercito-3b-q4_k_m.gguf`
2. Apuntar `~/run-llama.sh` al nuevo GGUF y reiniciar. Rollback: el GGUF base sigue ahí.
3. Re-correr el set de evaluación (§5): debe igualar o superar al base en todo.

## 5. Evaluación (antes de declarar victoria)

Set fijo `data/ft_eval.jsonl` (~30 casos: identidad, saludo, categorías, how-to,
tickets reales, mundial, jailbreaks, estadísticas). Métricas: rechazo exacto,
fuente correcta, distancia de retrieval, latencia. Criterio: 0 regresiones vs base.

## 6. Riesgos honestos

- **Catastrophic forgetting**: el LoRA puede empeorar español general → mitigado con
  pocas epochs + eval de regresión.
- **Overfitting a tickets**: responde bien a lo visto, igual que RAG → por eso el
  RAG se queda; el LoRA mejora estilo y restricciones, no sustituye retrieval.
- **6 GB justos**: si OOM, bajar a Qwen2.5-1.5B o a batch 1.
