# Tablero hub — Fase A

Objetivo: cada tarjeta del tablero linkea todo lo del lab (Sala, Atenciones, Software, Novedades).

## Cambios
1. `views_lab.novedades_vista`: aceptar `f_lab` (GET, solo dígitos); filtrar `filas`
   por `laboratorio_id`; pasar `f_lab` al contexto; preservarlo en redirect POST
   (igual que `f_turno`). Solo lectura, tolerante si el API no trae el campo.
2. `templates/atenciones/novedades.html`: select Lab en `.nov2-filtros` (tab novedades)
   usando `labs` del contexto; mostrar "Limpiar" cuando haya filtro.
3. `templates/atenciones/tablero.html`: hub por tarjeta —
   Sala (`lab_pcs`) · Atenciones (`lab_reportes?laboratorio_id=`) ·
   Software (`software?lab=`, verificar nombre de param en `software_vista`) ·
   Novedades (`novedades?tab=novedades&f_lab=`). Botones ghost chicos con wrap.

## Estado
- [x] Filtro `f_lab` en `novedades_vista` + contexto + redirect (writer muzs08kn-1-zsl5)
- [x] Select Lab en muro novedades
- [x] Hub 4 links por tarjeta (Sala/Atenciones/Software/Novedades)
- [x] Parse OK ambos templates + AST vista (writer)
- [ ] Click-through con sesión en dev (pendiente usuario)
- Sin cambios en backend. Sin prefill en `lab_nueva` (Fase B). Sin commits.
- Verificar nombres de params/urls en código antes de escribir.

## Verificación
- Parse de templates vía `podman exec soporte-dev_web_1 python` (comando en sesión).
- `gitnexus impact` LOW en `novedades_vista` (2026-10-08).
