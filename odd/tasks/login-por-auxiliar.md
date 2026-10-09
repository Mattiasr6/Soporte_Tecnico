# Login por auxiliar (una cuenta por persona)

## Objetivo
Cada Auxiliar y Encargado inicia sesión con su propia cuenta. Se elimina el flujo de identificación "a confianza" (`/auxiliares/soy/`) y se agrega `/auxiliares/perfil` para que cada uno gestione su cuenta (sobre todo la contraseña).

## Problema
- Hoy las cuentas Auxiliar/Encargado son compartidas; la persona se elige en sesión (`auxiliar_nombre`, `auxiliar_encargado`) en `views_lab.soy_vista`.
- La nómina (`backend-fastapi/data/equipo_auxiliares.json`) solo guarda `{nombre, activo, encargado}`: no hay vínculo con `Usuarios`. El backend valida la autoría por nombre normalizado (`laboratorios.py:682`, `software.py:330`), con fallback a `user.display_name`, que no se puede renombrar.

## Decisión (usuario, 2026-10-08)
Opción B: vincular cada entrada de la nómina a una cuenta (`usuario_id`) y resolver la identidad por cuenta, no por nombre tipeado.

## Alcance
- Backend: `usuario_id` opcional en la nómina, endpoint de vinculación, endpoint "quién soy en la nómina", y resolución de autoría por cuenta para roles Auxiliar/Encargado (auxiliar principal = nombre vinculado; los auxiliares extra siguen validándose por nombre).
- Frontend: identidad desde la cuenta (sin `soy`), aviso si la cuenta no está vinculada, vinculación desde `/usuarios`, `/auxiliares/perfil` con cambio de contraseña.

## Restricciones
- No romper roles Técnico/Jefe ni el `/perfil` de Soporte.
- Entradas de nómina existentes sin `usuario_id` siguen siendo válidas (migración suave).
- Artefactos en español neutro, consistente con el proyecto.

## Tareas
- [x] T1 Backend: `usuario_id` en nómina + `POST /api/laboratorios/equipo/vincular` + `GET /api/laboratorios/equipo/yo` + autoría por cuenta en laboratorios/software/novedades. Tests pytest.
- [x] T2 Frontend identidad: sesión toma el nombre vinculado al loguear; eliminar `soy` (ruta, vista, template, links); aviso de cuenta sin vincular; `puede_validar` desde el vínculo. Tests Django.
- [ ] T3 Frontend admin: en `/usuarios`, elegir miembro de nómina al crear Auxiliar/Encargado y vincular usuarios existentes. Tests Django.
- [ ] T4 `/auxiliares/perfil`: datos de la cuenta + cambio de contraseña, link en panel AUXILIARES, `/perfil` redirige ahí para Auxiliar/Encargado. Tests Django.

## Criterios de aceptación
- Un Auxiliar logueado registra atenciones/novedades/software con su nombre de nómina sin elegir nada.
- Una cuenta Auxiliar/Encargado sin vínculo ve un aviso claro y no puede registrar a nombre de otro.
- Auxiliar y Encargado cambian su contraseña desde `/auxiliares/perfil` y quedan logueados.
- `/auxiliares/soy/` ya no existe.

## Checks
- Backend: `cd backend-fastapi && pytest`
- Frontend: `cd frontend-django && python manage.py test`

## Entrega
Rama `feat/login-por-auxiliar` (desde `fix/ui-dev-round`). Pronóstico ~600–800 líneas → supera 400; estrategia `ask-on-risk`, se consulta al superar el umbral.

## Progreso
| Tarea | Ruta | Commit | Riesgo/review |
|---|---|---|---|
| T1 | delegada (writer; 5 archivos no triviales) | pendiente | gitnexus `_equipo`: CRITICAL (8 llamadores) → cambio aditivo |
| T2 | delegada (writer; views_lab/views/templates/tests) | pendiente | gitnexus `_quien_reporta`: HIGH (3 llamadores esperados: novedades/lab_pcs/software); `login_vista`, `lab_nueva_vista`: LOW |

**T1 evidencia:** Postgres desechable en Docker (`postgres:16-alpine`, tmpfs, :55433) + `alembic upgrade head` + seeds del proyecto + `setval` de secuencias + usuario Encargado de auditoría. Con T1: `2 failed, 195 passed`; base (HEAD sin T1, DB fresca): `2 failed, 182 passed`. Las 2 fallas son preexistentes (`test_seed::test_el_csv_se_puede_deduplicar_por_created_at` por datos del CSV; `test_equipo_crud_jefe_y_403_tecnico` por dict exacto, ajustado a `encargado`+`usuario_id`). Spot check tras el ajuste: `14 passed`. `test_equipo_vinculo.py` 13/13. Se quitó de `data/equipo_auxiliares.json` la entrada basura `TEST-LAB-aux` (la escribe `test_laboratorios._crear_atencion` sin restaurar; archivo gitignored).

**T2 evidencia:** helper `cargar_identidad_auxiliar` (views_lab) llamado tras login y re-login por contraseña; lee `GET /api/laboratorios/equipo/yo` → `auxiliar_nombre`/`auxiliar_encargado` en sesión (404/ApiError → se limpian). `_sin_vinculo` reintenta una vez por request (cubre vinculación posterior al login). Sin vínculo: novedades y nueva atención muestran el aviso y bloquean crear/devolver/validar/rechazar/enviar; marcar PC devuelve 403 JSON; timeline sin guard (solo lectura). `soy` eliminado (vista, URL, template, context processor, links "cambiar"). En nueva atención el auxiliar principal es fijo (readonly + forzado en servidor) para Auxiliar/Encargado; extras libres. RED: 8/10 tests nuevos (`IdentidadAuxiliarTest`) fallaban; GREEN: 10/10. Suite: 48 tests, 3 fallas preexistentes en base (`test_lista`, `test_navbar_auxiliar`, `test_navbar_jefe`). Runner: venv temporal Python 3.12 + requirements (el `.venv` del repo es symlink roto y Python 3.14 rompe Django 4.2), `DJANGO_SECRET_KEY=test`.

## Próximo paso
T3 vinculación desde `/usuarios`, luego T4 `/auxiliares/perfil`.
