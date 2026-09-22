# Pendientes para próximas specs

> Estado al 2026-09-22, rama `python-experiment`.
> Este documento es la fuente para armar las specs que siguen. Cada bloque trae el
> contexto ya investigado para que nadie tenga que re-descubrirlo.

---

## 0. Qué ya está hecho (no rehacer)

| Área | Estado |
|---|---|
| Backend FastAPI S1–S8 | completo · 60 tests |
| Django S9 (login, lista, registrar, modal ticket, sidebar, auxiliares) | completo · 28 tests |
| Dashboard S10 | completo (drill-down, ficha, calendario, sankey, donas, scatter, radar, presencia) |
| Selector de jerarquía en `/soporte` | árbol con filtro (reemplazó los 3 desplegables) |
| Paginación de la lista | 50 + "Ver más" (conserva filtros) |
| Esquema reproducible | `alembic upgrade head` crea las 6 tablas (antes era imposible: el baseline era no-op) |
| Código estable (slug) | columna `Codigo` única en los 3 niveles, backfill hecho, renombrar no la toca |
| API de escritura de jerarquía | CRUD de los 3 niveles + propagación de FK a las atenciones + `PATCH /atenciones/{id}/jerarquia` |
| Pantalla `/jerarquia` | árbol + detalle + alta/mover/renombrar/desactivar/eliminar |
| Carga de datos | 274 atenciones de septiembre, 53 áreas, 3 sectores, 4 grupos · invariante "jerarquía incoherente" = 0 |
| Backup de prod | pipeline arreglado (estaba generando 1.1M de archivos vacíos) + dump verificado por checksum |

---

## J1 · Bootstrap por código (la última pieza de jerarquía)

**Por qué**: la pantalla `/jerarquia` ya cambia el catálogo, pero el bootstrap
(`seed.py`) lee CSV **por nombre**. Un renombre deja los CSV viejos y un re-seed
sobre una BD vacía reconstruye la estructura anterior, en silencio.

**Por qué no se hizo con un export simple**: el export tendría que reescribir la
columna `area` del CSV de atenciones emparejando filas con la BD, y **hay
descripciones duplicadas** (5 grupos con misma descripción y fecha) → asignaría
áreas equivocadas sin avisar. Se descartó a propósito.

**La solución que el slug ya habilita**: que los CSV referencien por **código**.

| Archivo | Cambio |
|---|---|
| `mapeo-areas.csv` | `nuevo_nombre` → `codigo_destino` (144 filas, conversión única) |
| `atenciones_septiembre.csv` | columna `area` → `area_codigo` |
| `backend-fastapi/scripts/extraer_septiembre.py` | resolver el texto de prod → **código** (vía mapeo + catálogo) |
| `backend-fastapi/scripts/seed.py` | resolver el área por **código** |
| `backend-fastapi/scripts/exportar_catalogo.py` | **nuevo**: escribe el catálogo (con códigos) desde la BD. No toca el CSV de atenciones |

**DoD**: sobre una BD vacía, `alembic upgrade head` + `seed.py` reconstruye la
estructura **actual** (incluidos renombres y movimientos hechos por la GUI).

---

## J2 · Jerarquía, lo que quedó fuera de la v1

- **Movimiento en lote** (seleccionar varias áreas y moverlas juntas). Decisión del
  usuario: lo hace a mano. Solo tiene sentido si agrupar 24 áreas se vuelve tedioso.
- **Desactivar sectores**: `GruposPadres` **no tiene columna `Activo`** (solo
  `Nombre`, `Descripcion`, `Orden`). Hoy un sector solo se renombra, reordena, o se
  borra si está vacío. Agregar la columna es aditivo.
- **Sin drag & drop, a propósito**: mover reescribe N atenciones; un arrastre
  accidental sería un error silencioso. Se usa un diálogo explícito con el aviso de
  impacto. No cambiarlo sin decidirlo.
- **Unicidad de las áreas sin dependencia**: el `UniqueConstraint(GrupoPadreId,
  GrupoId, Nombre)` **no protege** a las 36 áreas con `GrupoId` NULL (Postgres trata
  cada NULL como distinto). La unicidad hoy la garantiza el chequeo de la app.

---

## P1 · `/perfil` — personalización y accesibilidad

**Requisito del usuario**: cada uno debe poder ver **su propio** perfil y jugar con
sus estadísticas. Los **Jefes** entran a `/perfil` y ven el suyo **y** el de los
técnicos. Ahí se retrabajan los 3 gráficos de técnicos que hoy viven en el dashboard
(scatter "carga vs fuera de turno", "rendimiento por técnico", "colaboraciones") más
el radar, que se aplana cuando el filtro tiene una sola categoría dominante.

**Hallazgo que define el trabajo**: `GET /api/atenciones/stats` **ya acepta
`usuario_id`** — no hay que agregar agregaciones. **Pero exige `is_privileged`**, así
que un técnico sin `can_view_dashboard` **no puede pedir ni sus propias stats**.
Decisión necesaria: endpoint propio (`/api/atenciones/mis-stats`, solo uno mismo) o
permitir el self en `get_stats`.

**Permisos**: técnico → solo lo suyo. Jefe → lo suyo y el de cualquier técnico.

**Parte barata, para separar en dos etapas**:
- **Etapa 1**: perfil como identidad + preferencias (nombre, especialidad —ya existe
  `PATCH /api/usuarios/{id}/especialidad`—, y preferencias personales). Es el lugar
  natural para las preferencias de **accesibilidad** (tamaño de fuente, contraste,
  movimiento reducido).
- **Etapa 2**: las estadísticas por técnico (los 3 gráficos + radar).

**Accesibilidad**: es transversal, no solo de `/perfil`. Hay un skill
`accessibility` disponible. Vale una pasada por todas las pantallas (foco, teclado,
contraste, `aria`), no solo por el perfil.

---

## N1 · `/notas` — bloc de notas

El más barato de todos: **el backend ya está listo** (`GET`/`PUT
/api/usuarios/notas`, un texto por usuario en `Usuarios.Notas`). Falta solo la
pantalla: un textarea con guardado. Hoy el sidebar tiene el botón "Bloc de notas"
sin acción.

---

## H1 · `/horarios`

Backend **completo**: `GET`/`POST`/`DELETE /api/horarios` + `GET /api/horarios/cobertura`
(mes + franjas). Referencia en v2: `frontend/src/app/horarios/page.tsx` (251 líneas).

**Hallazgo operativo**: **no hay horarios de septiembre cargados** (prod tiene 15 en
total, solo 2 de septiembre; el seed no los carga). Consecuencia: el turno no se
puede recalcular y el estado "fuera de turno" no se deriva automáticamente
(`estado_efectivo()` compara contra el horario del mes).

---

## R1 · `/reportes`

**Hay que decidir si es un feature real.** En v2 (`frontend/src/app/reporte/page.tsx`,
180 líneas) **no hace ningún `fetch`**: parece una maqueta. Si es real, definir qué
reportes y en qué formato (Excel, PDF, imprimible).

---

## L1 · `/launcher`

Portal con tarjetas de enlaces. Referencia en v2:
`frontend/src/app/launcher/page.tsx` (112 líneas, incluye una referencia de tokens de
diseño). No necesita backend.

---

## O1 · Operación y seguridad

- **HTTPS**: hoy es HTTP plano. El navegador ignora `Cross-Origin-Opener-Policy`
  (aviso benigno en consola) justamente por eso. `SECURE_SSL_REDIRECT=False`.
- **Backups**: el pipeline quedó arreglado, pero no hay alerta si vuelve a fallar.
  Vale un chequeo (tamaño > 0 y antigüedad < 2 días).
- **Cutover (S11)**: apagar .NET/Next y el compose definitivo. Sigue pendiente.

---

## D1 · Datos

- **La historia es solo septiembre (274 de 2212)**. Decisión del usuario: v2 arranca
  de 0 y v1 queda como evidencia de trabajo. Consecuencia: **S12 (migración de
  historia) sale del roadmap**.
- **`atenciones_septiembre.csv` es un snapshot**: prod sigue recibiendo atenciones
  (pasó de 253 a 274 en horas). Hay que re-extraerlo con `extraer_septiembre.py` en
  el momento de cargar, no usarlo tal cual.
- **56 filas con duplicados** (`fecha + área + categoría + descripción`, grupos de 2 y
  3). Puede ser legítimo (varias personas pidiendo lo mismo el mismo día). Sin revisar.
- **2 áreas huérfanas** (0 atenciones): `Sala 2 (Directorio)` y `Sala 3 (Directorio)`.
- **Los 25 registros sin jerarquía del dev viejo quedaron obsoletos**: se borraron al
  cargar de 0, y la carga nueva tiene **0 sin área**. Ya no hay nada que sanear.

---

## Decisiones ya tomadas (no volver a preguntar)

- Sectores: **Administrativos · Académicos · Espacios comunes · Instituciones**.
  `Eventos` sube a sector y pasa a llamarse "Espacios comunes"; se le suman
  `Sala Magna` y `Sala de lectura`. `Sala de Docentes` **se queda** en Vicerrectorado.
- `Sala 1/2/3 (Directorio)` pertenecen a `Instituciones › Directorio`.
- El sector de terceros se llama **"Instituciones"** (el jefe rechazó "Externos" por
  sonar excluyente). `EIAG` es posgrado y es empresa aparte → va como dependencia.
- Las empresas con subdivisiones van a nivel **dependencia**; sin subdivisiones,
  quedan como área directa del sector.
- Nombres de los niveles en la UI: **Sector → Dependencia → Área**.
- "Batch" → **"Lista"**.
- Movimiento en lote: **descartado** (el usuario lo hace a mano).

---

## Hallazgos que no hay que volver a investigar

- **No hay tablas fantasma** en la BD: 6 de negocio + `__EFMigrationsHistory` + `alembic_version`.
- **Categorías limpias**: las 8 de la BD son exactamente las 8 válidas.
- **`alembic/script.py.mako` faltaba** → `alembic revision` estaba roto en todo el
  proyecto. Agregado.
- **`0001_baseline` es no-op intencional** (el esquema lo poseía EF). La migración
  real es `de1d87cc0b82`.
- **`seed.py` siembra 10 usuarios**, no 9 (el docstring decía 9).
- **El PUT de atenciones** dejaba los 2 FK desincronizados si el cliente mandaba solo
  `area_id`. Arreglado.
- **`SessionLocal` es `autoflush=False`** y los modelos **no declaran
  `relationship()`**: hay que forzar los `flush()` en orden al sembrar.
- **Prod no tiene puerto mapeado al host**: se accede con
  `docker exec soporte-postgres psql -U soporte -d soporte`. IPs reales:
  `10.0.13.3` (prod) y `10.0.18.3` (dev), no `.2`.
- **`docs/traspaso-datos-septiembre.md`** (de otro agente) quedó desactualizado: §9
  dice 45 con colaborador (ahora son 55) y §7 recién ahora es cierto.
