# Slice 06 — Guardrails (el modelo contaba chistes)

## Objetivo

Que Wilmercito rechace fuera-de-tema y jailbreaks aunque el modelo falle.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> (Tras ver que el 1.5B contaba chistes ante "ignorá las reglas".)
> `Implementación de /ia/preguntar con defensa en profundidad.`

## Respuesta / acciones del agente

1. Medición previa: mundial → parafraseo amable (no exacto); jailbreak → chiste completo.
2. Diseño en 3 capas (backend, no en el prompt):
   - **Capa 1** prefiltro regex jailbreak → rechazo exacto sin llamar al motor.
   - **Capa 2** system + `Context/Question/Answer` al motor.
   - **Capa 3** postfiltro: marcadores fuera-de-tema → rechazo exacto; distancia > umbral → sin dato.
3. Verificado e2e: jailbreak → `Solo puedo responder...` + `rechazado: True`.

## Evidencia

- `app/routers/ia.py`: `_JAILBREAK`, `_MARCAS_FUERA_DE_TEMA`, `RECHAZO_EXACTO`, `SIN_DATO`
- Tests `test_ia_unit.py` (atraparon `olvidá` con tilde pasando el filtro)

## Decisión / hallazgo

- Modelos chicos: la restricción vive en código. El prompt solo es la capa 2 de 3.
