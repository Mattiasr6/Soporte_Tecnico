---
name: "no-coauthor-sisyphus"
description: "Auto-generado: commit, co-authored, sisyphus"
triggers:
  - "commit"
  - "co-authored"
  - "sisyphus"
  - "coauthor"
  - "firma"
  - "no coauthor sisyphus"
tags:
  - "git"
  - "commits"
  - "prohibido"
  - "generated"
auto-generated: true
source: "meta-learner"
generated-at: "2026-07-21"
---
# PROHIBIDO: Co-authored-by con Sisyphus

## Regla ABSOLUTA

NUNCA agregar `Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>` o cualquier variante en los commits. 

El usuario NO autoriza esto y considera que le robas crédito.

## Formato correcto de commit

```bash
git commit -m "fix: descripcion del cambio"
```

Sin trailers, sin co-autores, sin firmas adicionales. Solo el mensaje.

## Qué hacer si ves esto en el código

Si ves un commit existente con esta linea, NO la borres del historial (reescribir historia es peligroso). Solo asegurate de NO agregarla en commits futuros.

## Checklist pre-commit

- [ ] El mensaje NO tiene lineas de Co-authored-by
- [ ] El mensaje NO tiene firmas de Sisyphus ni de ningún agente
- [ ] Solo el mensaje de commit, nada más

Regla válida para TODOS los agentes que trabajen en este repositorio.

