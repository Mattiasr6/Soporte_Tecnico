# KPI captura real

Problema: semáforo con captura rota — amarillo siempre 0 (Django jamás envía
`pc_nombre`), rojo solo si eligen lab (opcional), verde miente ("limpios").

## Cambios
1. `laboratorios_nueva.html` + `_items_lab_desde_post`: campo PC opcional
   (`name="pc_nombre"`, backend `LabAtencionCreate.pc_nombre: str | None`).
   Verificar en código dónde se eligen los labs del item y poner el campo ahí
   cerca; verificar largo máximo de columna en `backend-fastapi/app/models/`.
2. `novedades.html`: Lab requerido en form de objetos (atributo `required`).
3. `tablero.html`: "En verde (limpios)" → "En verde (sin pendientes)".

## Estado
- [x] Campo PC opcional en nueva atención + payload (writer muzsdc2z-2-f3r8)
- [x] Lab requerido en objetos
- [x] Label verde honesto
- [x] Parse OK 3 templates + py_compile/AST vista
- Nota: `pc_nombre` aplica al batch completo (un valor por envío)
- Sin cambios en backend. Sin commits. Parse de templates vía podman igual que Fase A.
