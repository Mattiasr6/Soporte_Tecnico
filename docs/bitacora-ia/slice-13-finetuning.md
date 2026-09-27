# Slice 13 — Fine-tuning (3 noches, resultado negativo honesto)

## Objetivo

Enseñarle el dominio al 3B con QLoRA nocturno (Unsloth, RTX 2060 6 GB).

## Prompts

> `me interesa lo del modelo para fine-tuning tenemos tiempo para realizarlo serias capaz de documentarlo al mismo tiempo correctamente en .md?`
> `comenzemos, ¡VAMO A ELLO!, (guarda esa frase tal cual siempre que querramos comenzar a implementar)`
> `no podemos lanzarlos mas temprano?, despues de todo estamos en una rama de desarrollo`

## Respuesta / acciones del agente

1. Env: Python 3.12 vía `uv` (3.14 sin torch), torch 2.8 cu126 + torchao 0.14 + transformers 4.57 + trl 0.29 (4 combinaciones fallidas documentadas) + bitsandbytes; Turing sin bf16 → fp32.
2. Dataset 2229 pares (tickets+KB+feedback+5 rechazos) + validación (atraparon duplicados; ~500 descripciones repetidas en tickets).
3. Prueba 10 steps OK (loss 3.25). Noche 1: 279 steps, loss → 0.77.
4. **Eval 5/30, 5 jailbreaks → gate frenó el despliegue, rollback al base.** Causas descartadas: formato Alpaca (Noche 3 con chat template: mismo 5/30).
5. Diagnóstico: 2200 tickets enseñan "responde todo servicial"; 15 ejemplos no pesan. Plan Noche 4: subsample 500 + curado ×100 + LR 2e-5.

## Evidencia

- `scripts/ft/` (build/validate/train/test/nightly), `data/ft_eval.jsonl` (30 casos), `docs/specs/ft-noche1.md` + bitácora de noches
- `train_runtime 571s, loss 0.77`; evals `5/30` archivados

## Decisión / hallazgo

- Un resultado negativo medido vale más que un despliegue roto: el gate existe para esto.
- "¡VAMO A ELLO!" quedó guardada como frase de inicio de implementación.
