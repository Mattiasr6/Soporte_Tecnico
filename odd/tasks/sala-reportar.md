# Reportar atención desde sala (prefill lab+PC)

Flujo: en sala, 1 PC seleccionada → botón "Reportar" → `lab_nueva?lab=<id>&pc=<nombre>`
con ambos campos prellenados. Sin cambios en backend, sin commits.

## Cambios
1. `views_lab.lab_nueva_vista` (SOLO additivo al final, antes del render):
   leer `lab` (dígitos, debe existir en `cards["activas"]`) y `pc` (texto ≤50)
   de GET; pasar `lab_prefill` (int o None) y `pc_prefill` (str) al contexto.
2. `laboratorios_nueva.html`: radio de lab chequeado si no hay `edit_item` y
   `lab.id == lab_prefill`; input `pc_nombre` usa `pc_prefill` como default
   (solo cuando no hay `edit_item`).
3. `laboratorios_pcs.html`: en `#ed-acciones`, link "Reportar" visible solo con
   1 PC seleccionada con nombre; JS arma URL con `encodeURIComponent` usando
   `{{ lab_id }}` del contexto. Estilo `.btn` coherente.

## Estado
- [x] Prefill `?lab&pc` en `lab_nueva_vista` + contexto (writer muzsh3j0-3-swie)
- [x] Radio lab + PC prellenados en nueva atención
- [x] Botón Reportar en sala (1 PC con nombre)
- [x] Parse + bordes OK
- [ ] Probar flujo con sesión en dev
- Parse templates vía podman + py_compile vista. Probar lógica de query con
  valores borde (`?lab=abc`, `?lab=999`, sin params → sin prefill, sin error).
