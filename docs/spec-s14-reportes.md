# Spec S14 — Reporte mensual para rectorado ("calidad Power BI", solo impresión)

```yaml
---
title: "S14 — Reporte mensual / acumulado anual imprimible para el rector"
status: "approved"
version: "1.0"
priority: "alta"
estimated_effort: "2-3 días"
dependencies: ["GET /api/atenciones/stats (existente)", "ECharts vendored + dashboard.js (referencia)", "tokens.css + base.html + _navbar.html (convenciones)"]
---
```

## Historias de usuario

> **Como** jefe del área de Soporte Técnico (Wilmer Cerruto), **quiero** un reporte mensual del trabajo del equipo, con calidad de presentación tipo Power BI, **para** presentarlo al rector de la universidad como documento formal del trabajo realizado.

> **Como** jefe, **quiero** alternar entre el mes seleccionado y el acumulado del año **para** mostrar tanto el mes en contexto como el avance anual.

## Objetivo

Un documento formal de período cerrado, imprimible a PDF vía diálogo del navegador, que lee como BI (KPIs con comparación, evolución, desgloses, top 10, casos destacados) sin exportar datos ni rankear técnicos.

## Decisiones heredadas (cerradas — no reabrir)

1. **Solo imprimible.** Mecanismo de entrega: diálogo de impresión del navegador → "Guardar como PDF", con stylesheet `@media print`. Cero librerías nuevas.
2. **Sin sección por técnico.** Nada de `por_tecnico`, `por_tecnico_fuera`, `por_tecnico_categoria`, `asistencias`, scatter, radar, rendimiento ni colaboraciones. El rector no necesita saberlo.
3. **Ambos períodos:** mes seleccionable + vista acumulada del año (YTD).
4. **Solo Jefes / `can_view_dashboard`.** Misma puerta que `/dashboard/` (`_puede_dashboard`; sin permiso → redirect a `atenciones_lista`, igual que `dashboard_vista`).

---

## Stack Tecnológico (OBLIGATORIO)

| Capa | Tecnología | Versión | Notas |
|------|-----------|---------|-------|
| Backend | FastAPI + SQLAlchemy sync + psycopg | repo actual | SIN CAMBIOS. Solo se consume `GET /api/atenciones/stats` y `GET /api/atenciones` |
| Frontend | Django templates server-rendered | repo actual | Vista en `atenciones/views.py`, ruta en `atenciones/urls.py`, template que extiende `atenciones/base.html` |
| Estilos | CSS plano en `frontend-django/static/css/tokens.css` | actual | Sin build, sin framework, sin Tailwind. Nuevas reglas se agregan a `tokens.css` (incluido el bloque `@media print`) |
| Charts | ECharts vendored (`static/js/vendor/echarts.min.js`) | actual | Mismo script tag + `?v={{ asset_version }}` que `dashboard.html`. Lógica nueva en `static/js/reportes.js` espejando `dashboard.js` (paleta VERDE/DORADO, `montar`, `barrasH`, donas, `.sin-datos`) |
| Auth/gate | Sesión Django + `_puede_dashboard` | actual | `Jefe` o `can_view_dashboard`. Contexto (`can_dashboard`, `nav_page`, `asset_version`) ya lo provee `context_processors.py` |
| Tests | pytest backend + Django tests | 85 + 38 | Ambos suites deben seguir verdes |

---

## Arquitectura

### Diagrama de componentes (textual)

```
[Django: /reportes/?mes=YYYY-MM&vista=mes|anio] --HTTP--> [FastAPI: GET /api/atenciones/stats x3] --> [DB: Atenciones + Jerarquía]
[Django: misma vista]                           --HTTP--> [FastAPI: GET /api/atenciones?limit=2000] --> [filtro por mes en la vista] --> [Trabajo destacado]
[Template: reportes.html + reportes.js] <-- payload via json_script <-- [vista: kpis + charts + destacados + metodologia]
[Navegador: Ctrl+P / Guardar como PDF] <-- @media print en tokens.css <-- [mismo DOM, sin nav/filtros/botones]
```

No hay modelo nuevo, no hay migración, no hay endpoint nuevo.

### Mapa de archivos

```
# Archivos a crear:
frontend-django/templates/atenciones/reportes.html   # documento imprimible, extiende atenciones/base.html
frontend-django/static/js/reportes.js                # ECharts del reporte (evolución, categorías, sectores, 2 donas)
docs/spec-s14-reportes.md                            # esta spec

# Archivos a modificar:
frontend-django/atenciones/views.py                  # + reportes_vista + helpers _periodo_reporte/_kpis_reporte/_destacados (espejo dashboard_vista)
frontend-django/atenciones/urls.py                   # + path("reportes/", views.reportes_vista, name="reportes")
frontend-django/templates/atenciones/_navbar.html    # placeholder "Reportes · PRONTO" pasa a link real (nav_page reportes)
frontend-django/static/css/tokens.css                # + sección reporte: kpi-delta, destacado, tabla top10, bloque @media print

# Archivos a NO tocar:
backend-fastapi/**                                   # sin cambios de backend
frontend-django/templates/atenciones/dashboard.html  # el dashboard exploratorio no se toca
frontend-django/static/js/dashboard.js               # solo referencia de patrones, no se modifica
```

---

## Contratos de Datos

### API — llamadas exactas que hará la implementación

La vista Django llama al backend con el JWT de sesión vía `api_get`. Rango de mes: día 1 → último día (`calendar.monthrange`).

**Vista `mes` para `mes=YYYY-MM` (3 llamadas `stats` + 1 `lista`):**

```
// S_mes — el mes del reporte
GET /api/atenciones/stats?desde_dia=1&desde_mes=MM&desde_anio=YYYY&hasta_dia=LD&hasta_mes=MM&hasta_anio=YYYY

// S_prev — mes anterior (para la comparación MoM; cruza año en enero)
GET /api/atenciones/stats?desde_dia=1&desde_mes=MP&desde_anio=YP&hasta_dia=LP&hasta_mes=MP&hasta_anio=YP

// S_anio — enero → fin del mes del reporte (para la línea de evolución anual)
GET /api/atenciones/stats?desde_dia=1&desde_mes=1&desde_anio=YYYY&hasta_dia=LD&hasta_mes=MM&hasta_anio=YYYY

// L_mes — universo para "Trabajo destacado" (el backend NO filtra por fecha:
// la vista filtra en memoria por fecha_registro[:7] == "YYYY-MM")
GET /api/atenciones?limit=2000
```

**Vista `anio` (`?vista=anio&mes=YYYY-MM`, YTD enero → mes M):** una sola llamada:

```
// S_ytd — acumulado enero → fin del mes M (reusa como S_anio para la evolución)
GET /api/atenciones/stats?desde_dia=1&desde_mes=1&desde_anio=YYYY&hasta_dia=LD&hasta_mes=MM&hasta_anio=YYYY
```

Sin comparación MoM en vista `anio` (el delta MoM solo existe en vista `mes`). "Trabajo destacado" en vista `anio`: se omite (el reporte anual con casos sueltos pierde foco; ver RN-08).

Bloques de `StatsOut` usados (el resto se ignora y no se pide nada nuevo): `total`, `fuera_de_turno`, `por_categoria`, `por_mes`, `por_area`, `por_medio`, `por_tipo_solicitante`, `por_padre`. Prohibidos en este reporte: `por_tecnico`, `por_tecnico_fuera`, `por_tecnico_categoria`, `asistencias`.

Forma de respuesta (ya existente, no cambia):

```typescript
interface StatsOutUsado {
  total: number;
  fuera_de_turno: number;
  por_categoria: { categoria: string; total: number }[];
  por_mes: { anio: number; mes: number; total: number }[];
  por_area: { area: string; total: number }[];
  por_medio: { medio: string; total: number }[];
  por_tipo_solicitante: { tipo: string; total: number }[];
  por_padre: { id: number; nombre: string; total: number }[];
}
interface AtencionLista {
  id: number; fecha_registro: string; area_solicitante: string;
  categoria: string; descripcion: string; solucion: string;
  usuario_nombre: string; fuera_de_turno: boolean;
}
```

### Modelo de Base de Datos

Sin cambios. Sin migración.

```sql
-- N/A: esta spec no crea ni altera tablas.
```

### Frontend — payload vista → template/JS

La vista calcula en servidor y entrega `payload` vía `{{ payload|json_script:"payload" }}` (igual que dashboard):

```typescript
interface ReportePayload {
  periodo: { vista: "mes" | "anio"; mes: string; etiqueta: string; es_mes_en_curso: boolean };
  kpis: {
    total: number; prev_total: number | null;
    delta_abs: number | null; delta_pct: number | null;  // null = previo sin datos → ver RN-04
    fuera_pct: number; fuera_delta_pts: number | null;
    promedio_dia: number; dias_periodo: number;
    areas_distintas: number;
  };
  charts: {
    evolucion: { labels: string[]; values: number[] };       // de S_anio.por_mes, año YYYY, meses 01..M
    categoria: { labels: string[]; values: number[] };       // de S_mes.por_categoria desc
    sectores: { labels: string[]; values: number[] };        // de S_mes.por_padre
    medio: { labels: string[]; values: number[] };
    tipo_solicitante: { labels: string[]; values: number[] };
    top_areas: { area: string; total: number; pct: number }[]; // top 10 de S_mes.por_area
  };
  destacados: { id: number; area: string; categoria: string; descripcion: string; solucion: string }[];
  metodologia: { fuente: string; periodo: string; generado_en: string; corte: string };
}
```

Estados del documento: `loading` no aplica (server-render; los charts ECharts se montan al cargar). `empty` / `error` según § Definición de Estados de UI.

---

## Flujo Principal

**F1 — Abrir el reporte del mes (vista `mes`):**

1. Jefe abre `/reportes/` (sin params → redirige a `?mes=<mes actual America/La_Paz>&vista=mes`).
2. Vista valida `mes=YYYY-MM` (formato + rango 01..12) y `vista=mes|anio`; si inválido → cae al mes actual con `vista=mes`.
3. Vista hace S_mes + S_prev + S_anio + L_mes (4 GET al backend con el JWT de sesión).
4. Vista calcula KPIs (RN-01..RN-05), arma `charts`, elige destacados (RN-06), arma `metodologia` (RN-09).
5. Template renderiza: header → KPIs con delta → evolución → categorías → sectores → donas → top 10 → destacados → footer metodología.
6. `reportes.js` monta los 5 charts ECharts desde `payload` (evolución línea, categorías barras H, sectores barras H, 2 donas).
7. Jefe pulsa "Imprimir / Guardar PDF" → diálogo del navegador → PDF (contrato print § abajo).

**F2 — Vista acumulada (`?vista=anio&mes=YYYY-MM`):** igual que F1 pasos 5-7, pero con S_ytd como fuente única, header "Acumulado enero–<Mes YYYY>", sin fila de deltas MoM (los KPI cards muestran el valor YTD sin ▲▼), sin sección destacados.

### Flujo Alternativo — FA-01 mes sin atenciones

1. Si S_mes.total == 0: KPIs en 0 (delta → "s/d", RN-04), cada chart muestra `.sin-datos` "Sin atenciones registradas en este período", top 10 muestra el mismo mensaje, destacados se reemplaza por nota "Sin casos para destacar en este período".
2. Evolución anual y footer se renderizan igual (la línea puede tener hueco en M).

### Flujo Alternativo — FA-02 mes en curso (corte a mitad de mes)

1. Si `mes` == mes actual: footer lleva `corte: "Datos al <hoy> — mes en curso, cifras parciales"` (RN-09); header muestra etiqueta "Septiembre 2026 (parcial)".
2. Si mes pasado: `corte: "Mes cerrado"`.

### Flujo de Error

| Condición | Respuesta | HTTP Status | Mensaje |
|-----------|-----------|-------------|---------|
| Sin sesión | redirect login | 302 | (vía `@con_login`) |
| Sin `can_view_dashboard` | redirect lista | 302 | (igual que `dashboard_vista`) |
| `mes`/`vista` inválidos | fallback a mes actual + vista mes | 200 | sin mensaje (URL canónica en la barra) |
| Backend `stats` falla | página de error del reporte | 502 | "No se pudo cargar el reporte. Reintentá." + botón reintentar |
| Backend `lista` falla (solo afecta destacados) | reporte sin destacados | 200 | nota "No se pudieron cargar los casos destacados" en esa sección |

---

## Catálogo de Errores

| Código | HTTP | Condición | Mensaje visible | Log |
|--------|------|-----------|----------------|-----|
| REP-001 | 302 | Sin permiso (`_puede_dashboard` falso) | redirect `atenciones_lista` | nivel info |
| REP-002 | 200 | Param `mes`/`vista` inválido | fallback silencioso al mes actual | nivel info |
| REP-003 | 502 | `api_get stats` lanza `ApiError` | "No se pudo cargar el reporte. Reintentá." | nivel error (detalle backend) |
| REP-004 | 200 | `api_get lista` lanza `ApiError` | nota en sección destacados | nivel warn |
| REP-005 | 200 | S_mes.total == 0 | estados vacíos (no es error) | nivel info |
| REP-006 | 200 | S_prev.total == 0 con S_mes.total > 0 | delta "s/d" + "+N" absoluto (RN-04, evita div/0) | nivel info |

---

## Reglas de Negocio

1. **RN-01 (KPIs vista mes, exactamente 5):** total atenciones (S_mes.total) · mes anterior + delta (S_prev.total, ▲▼ % + absoluto) · % fuera de turno (fuera/total·100, 1 decimal + delta en puntos vs S_prev) · promedio por día (total / días calendario del mes, 1 decimal) · áreas distintas atendidas (`len(S_mes.por_area)`).
2. **RN-02 (sectores):** barras por `por_padre` (nombre/total desc). Son siempre 3 (`Administrativos · Académicos · Instituciones`).
3. **RN-03 (top 10):** `por_area` desc, 10 filas, columnas Posición · Área · Atenciones · % del mes. Empates: orden alfabético como desempate estable.
4. **RN-04 (división por cero):** si S_prev.total == 0: delta_pct = null → render "s/d" + "+N" absoluto con nota "mes previo sin registros". Si ambos 0 → "— sin variación". Nunca mostrar `inf%` ni `NaN%`. Aplica igual a `fuera_delta_pts`.
5. **RN-05 (promedio):** días calendario del mes (`monthrange`), no días hábiles ni días con actividad. Vista `anio`: total / días calendario enero→M.
6. **RN-06 (destacados, default):** heurística determinista — por cada una del top-3 categorías del mes, 1 atención de L_mes filtrada al mes y a esa categoría, eligiendo la de `solucion` más larga (len); desempate por `id` menor. Máximo 3 casos. Campos mostrados: área, categoría, descripción, solución. Sin nombres de técnicos.
7. **RN-07 (prohibición técnico):** ningún bloque, tabla, tooltip ni label menciona técnicos, rendimientos ni colaboraciones. Los datos `por_tecnico*`/`asistencias` ni siquiera se leen en la vista.
8. **RN-08 (vista anio):** sin deltas MoM, sin destacados; la evolución muestra enero→M del año; header y footer dicen "acumulado".
9. **RN-09 (metodología):** footer siempre visible con fuente (`GET /api/atenciones/stats`), período exacto (`01/09/2026–30/09/2026`), generado-en (`America/La_Paz`, `%d/%m/%Y %H:%M`), y corte ("Mes cerrado" o "Datos al <hoy> — mes en curso").
10. **RN-10 (URLs compartibles):** todo estado vive en querystring GET (`?mes=YYYY-MM&vista=mes|anio`). El selector es GET (bookmarkable). Sin estado en sesión ni localStorage.

---

## Decisión abierta explícita (D-01 — Trabajo destacado)

> El usuario elige. El implementador aplica la opción por defecto salvo instrucción contraria. No hay tercera opción.

- **Opción A (default, sin backend):** heurística RN-06. Reproducible, sin datos nuevos, muestra amplitud (una por categoría top-3). Riesgo: la solución más larga no siempre es la más notable.
- **Opción B (con backend, spec delta aparte):** flag manual `destacar` en la atención (columna + `PATCH` + checkbox en el ticket + filtro en el reporte). Da control editorial al jefe pero es trabajo de backend + migración + UI, fuera del "sin backend" de esta spec.

---

## Criterios de Aceptación (Gherkin)

```gherkin
Feature: Reporte mensual para rectorado

  Background:
    Given sesión de Jefe con can_view_dashboard
    And DB dev con atenciones de septiembre 2026

  Scenario: Happy path — reporte del mes
    Given voy a "/reportes/?mes=2026-09&vista=mes"
    Then veo header "Reporte mensual — Soporte Técnico · Septiembre 2026"
    And veo 5 KPIs con delta MoM vs agosto
    And veo evolución anual con septiembre marcado
    And veo categorías, sectores (3), 2 donas, top 10 y 3 destacados con solución
    And el footer cita fuente, período, generado-en y corte

  Scenario: Vista acumulada
    Given voy a "/reportes/?mes=2026-09&vista=anio"
    Then el header dice "Acumulado enero–septiembre 2026"
    And los KPIs no muestran deltas MoM
    And no hay sección de destacados

  Scenario: Mes sin datos evita división por cero
    Given voy a un mes con 0 atenciones y previo también 0
    Then los KPIs muestran 0 y el delta "— sin variación"
    And cada chart muestra "Sin atenciones registradas en este período"

  Scenario: Previo en cero con mes actual positivo
    Given S_prev.total es 0 y S_mes.total es mayor a 0
    Then el delta muestra "+N" absoluto y "s/d" en vez de porcentaje

  Scenario: Sin permiso
    Given sesión de técnico sin can_view_dashboard
    When voy a "/reportes/"
    Then redirige a la lista de atenciones

  Scenario: Sin técnicos en el documento
    Given el reporte renderizado de cualquier período
    Then ningún nombre de técnico aparece en el HTML ni en tooltips

  Scenario: Impresión
    When imprimo a PDF desde el navegador
    Then el PDF no contiene nav, filtros ni botones
    And ningún chart ni KPI queda cortado entre páginas
```

---

## Mockups ASCII

```
+-------------------------------------------------------------+
| REPORTE MENSUAL — SOPORTE TÉCNICO (UPDS)                    |
| Septiembre 2026 · Equipo de Soporte Técnico · generado ...  |
| [mes: 2026-09] [vista: Mes|Acumulado] [Imprimir / Guardar]  |
+-------------------------------------------------------------+
| [KPI total 276 ▲12% (+30)] [prev 246] [fuera turno 8,3%]   |
| [promedio/día 9,2] [áreas distintas 41]                     |
+-------------------------------------------------------------+
| EVOLUCIÓN 2026 (línea, ene→sep)                             |
+-------------------------------------------------------------+
| POR CATEGORÍA (barras H)                                    |
+-------------------------------------------------------------+
| DÓNDE SE CONCENTRÓ (sectores, barras H)                     |
+-------------------------------------------------------------+
| CÓMO LLEGÓ (dona)  |  QUIÉN PIDIÓ (dona)                    |
+-------------------------------------------------------------+
| TOP 10 ÁREAS (tabla: pos · área · atenciones · %)           |
+-------------------------------------------------------------+
| TRABAJO DESTACADO (3 casos: área, categoría, desc, solución)|
+-------------------------------------------------------------+
| Metodología: fuente ... · período ... · corte ...           |
+-------------------------------------------------------------+
```

---

## Contrato de impresión (`@media print` en `tokens.css`)

- `@page { size: A4; margin: 14mm 12mm; }`.
- Ocultar en print: `.sidebar`, `.nav-mobile-toggle`, `.scrim`, el `form` de filtros/selector, `.btn`, `.link-btn`, `.no-print`.
- `.page-wide` en print: `max-width: none; margin: 0; border: 0; padding: 0; background: #fff;`.
- `break-inside: avoid` en `.bloque`, `.kpi`, `.destacado`, filas `.tabla tr`; los headers de sección con `break-after: avoid`.
- Charts: altura fija de impresión (evolución 220px, barras 240px, donas 220px); `reportes.js` re-hace `resize()` en `beforeprint`/`afterprint` para que el canvas no salga recortado.
- Colores: `-webkit-print-color-adjust: exact; print-color-adjust: exact;` solo en `.kpi b`, `.tabla thead th`; el resto debe leerse en B/N (texto oscuro sobre blanco, sin depender del fondo verde).
- El botón "Imprimir" es `window.print()` y lleva clase `no-print`.

## Contrato del selector de período

- Un `<input type="month" name="mes">` (mismo control que `/atenciones/`) + un toggle `vista` (dos radios o segmented: "Mes" / "Acumulado del año") + submit GET.
- URL canónica: `/reportes/?mes=YYYY-MM&vista=mes|anio`. Sin params → 302 a la canónica del mes actual (zona `America/La_Paz`, reusar `_mes_actual()`).
- Etiquetas: mes → "Septiembre 2026" (reusar `MESES` de views.py); `anio` → "Acumulado enero–septiembre 2026". Mes en curso agrega "(parcial)".

## Definición de Estados de UI

| Estado | Condición | Render |
|--------|-----------|--------|
| Success | S_mes.total > 0 | Documento completo |
| Empty | S_mes.total == 0 | KPIs en 0, `.sin-datos` en cada chart, nota en destacados; evolución y footer normales |
| Error stats | `ApiError` en S_* | Bloque error "No se pudo cargar el reporte. Reintentá." + botón reintentar (GET a la misma URL) |
| Error lista | `ApiError` en L_mes | Solo la sección destacados muestra la nota de fallo |
| Loading charts | ECharts cargando | Los contenedores tienen altura fija; si `echarts` falta, el `reportes.js` no corre y queda el HTML server-render (KPIs, top 10, destacados, footer intactos) |

---

## Definition of Done (DoD)

1. [ ] Ver `/reportes/?mes=2026-09&vista=mes`: header, 5 KPIs con ▲▼ vs agosto, evolución, categorías, 3 sectores, 2 donas, top 10, 3 destacados, footer metodología.
2. [ ] Ver `/reportes/?mes=2026-09&vista=anio`: acumulado sin deltas ni destacados.
3. [ ] Ver mes vacío: ceros + "s/d" o "— sin variación", `.sin-datos` en charts, sin `NaN`/`inf` en el HTML.
4. [ ] Ver como técnico sin permiso: redirect a lista. Como Jefe: 200.
5. [ ] Imprimir a PDF (Chrome): sin nav/filtros/botones, sin cortes dentro de charts/KPIs, legible en B/N, `.page-wide` sin borde ni límite de 900px.
6. [ ] Buscar nombre de cualquier técnico en el HTML del reporte: 0 coincidencias.
7. [ ] `python manage.py test` (Django, 38 tests) verde + `pytest` backend (85 tests) verde.
8. [ ] Sin comentarios ni docstrings nuevos en el código (política del proyecto: el hook los bloquea).
9. [ ] Navbar muestra "Reportes" como link real (el placeholder `pronto` desaparece) con `active` en la página.
10. [ ] URL compartible: recargar/bookmark de la URL canónica reproduce el mismo reporte.

---

## Orden de Implementación

1. **Paso 1 — ruta + vista + gate:** `urls.py` (`reportes/`), `reportes_vista` con `_puede_dashboard` + `_periodo_reporte` (parseo `mes`/`vista`, fallback canónico) — verificar 302/200 a mano.
2. **Paso 2 — datos:** S_mes/S_prev/S_anio (+S_ytd) + L_mes con filtro en memoria; `_kpis_reporte` con RN-01/RN-04/RN-05; `_destacados` con RN-06.
3. **Paso 3 — template + navbar:** `reportes.html` (header, KPIs, secciones, top 10, destacados, footer) + link real en `_navbar.html` (`nav_page="reportes"`).
4. **Paso 4 — charts:** `reportes.js` (5 ECharts espejando `dashboard.js`) + `payload` vía `json_script`.
5. **Paso 5 — estilos + print:** sección reporte en `tokens.css` + bloque `@media print` (contrato de arriba); probar Ctrl+P → PDF.
6. **Paso 6 — vacíos/errores + DoD:** FA-01/FA-02, REP-002..006, suite completa verde.

El orden sigue la regla: **datos → lógica → presentación → tests**. Sin tests nuevos obligatorios salvo que el implementador vea hueco barato (p.ej. parseo de `mes` inválido); los existentes deben seguir verdes.

---

## Lo que NO está en alcance (explícito)

- ❌ Exportar Excel/CSV (decisión cerrada: solo impresión).
- ❌ Generación de PDF en servidor, servicio de impresión, ni librerías nuevas.
- ❌ Cambios de backend (incluida la Opción B de D-01: requiere spec delta aparte).
- ❌ Cualquier ranking o mención por técnico.
- ❌ Duplicar el dashboard: lo idéntico se justifica — evolución/categorías/medio/tipo/top10 pertenecen al reporte porque el rector necesita el mes cerrado en contexto anual sin interactividad; drill-down, ficha, calendario, sankey, scatter, radar, heatmap y colaboraciones NO entran (son exploratorios o de gestión interna).
- ❌ Filtros jerárquicos (sector/dependencia/área) ni rango arbitrario: el reporte es del equipo completo, un período a la vez.
- ❌ Comentarios/docstrings en el código (bloqueados por hook del proyecto).

---

## Brechas genuinas que esta spec no puede cerrar

1. **Calidad de los destacados (RN-06):** "solución más larga" es un proxy de "caso notable", no una garantía. Solo el usuario (D-01) lo resuelve.
2. **Techo de `limit=2000` en `L_mes`:** sobra hoy (~276/mes), pero si un mes supera 2000 atenciones los destacados se elegirían sobre una muestra truncada. Sin filtro por fecha en el backend no hay arreglo sin backend.
3. **Fidelidad de impresión de canvas ECharts:** depende del navegador (verificar en Chrome); si un chart sale recortado, ajustar alturas de impresión del contrato, no agregar librerías.
