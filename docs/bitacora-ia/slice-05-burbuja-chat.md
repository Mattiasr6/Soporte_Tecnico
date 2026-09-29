# Slice 05 — Burbuja de chat (invisible → visible)

## Objetivo

Chat de Wilmercito como burbuja en `frontend-django`, solo con sesión.

## Prompts (transcripción editada para legibilidad; contenido y decisiones intactos)

> `No veo ninguna burbuja, la verdad.`

> `Mmm, nop. Entré desde una pestaña de incógnito y tampoco veo nada abajo a la derecha, ni nada.`

> `Estoy entrando y reiniciando la página, todo. No veo nada azul con la W abajo. Estoy en http://100.90.209.98:8011/.`

## Respuesta / acciones del agente

1. Primera hipótesis (CSS): la burbuja existía en el HTML pero sin estilos → creado `static/css/wilmercito.css` (commit `7bed2ff`). Usuario: seguía sin verse.
2. Segunda hipótesis (caché/sesión): verificado por fuera (login + HTML contiene botón) → el usuario no había iniciado sesión en incógnito. Usuario: sí estaba logueado.
3. Diagnóstico real con navegador Playwright como el usuario: el botón **sí estaba en el DOM** pero con `position:static` gris → el CSS no cargaba. Causa: el proceso web arrancó **antes** de sincronizar el `<link>` y Django cachea templates en memoria.
4. Fix: `systemctl restart soporte-web-ia` → botón 56×56 fijo azul abajo-derecha. Captura de verificación.

## Evidencia

- Commit `7bed2ff`; capturas Playwright (botón gris → botón azul)
- `getComputedStyle`: `static/rgb(239,239,239)` → `fixed/rgb(26,86,219)`
- Prueba externa: login → `wilmercito-btn: True` → `/wilmercito/` responde `kb_medios`

## Decisión / hallazgo

- Debug por capas (DOM → estilos → caché de templates) en vez de adivinar; captura como evidencia.
