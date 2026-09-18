# Handoff — Rediseño V2.x hacia OpenDesign

Fecha: 2026-09-15 · Estado: **COMPLETADO — prototipo generado y verificado en navegador**

Resultado: [preview](http://127.0.0.1:7456/api/projects/soporte-redesign-2x/raw/index.html) ·
[studio](http://127.0.0.1:7456/projects/soporte-redesign-2x/conversations/e06a8f4f-4f55-4cd0-9131-0ae917c2fde3/files/index.html)
(links válidos solo en la sesión actual del daemon; si OpenDesign reinicia, pedir de nuevo `get_run`).
Ver §6 para el detalle del run y la verificación.

## 1. Bloqueo resuelto: MCP OpenDesign 403

Todas las rutas `/api` del MCP devolvían:

```
daemon 403 on http://localhost:7456/api/<ruta>: {"error":"Powered preview origin cannot access this API route"}
```

### Causa raíz (reproducida)

`/home/mattias/.open-design/mcp-server/server.js:1893-1919`. El daemon escucha en `0.0.0.0` →
`reportHostForPoweredPreview()` = `'127.0.0.1'` → `poweredPreviewHost()` = `'localhost'`.

El guard rechaza con 403 toda request que cumpla:

- `Host` = `localhost:7456` (== `poweredHost` + `resolvedPort`), **y**
- algún header `sec-fetch-*` presente (que Node/undici añade por su cuenta), **y**
- path fuera de `/api/projects/{id}/powered/...`

Prueba con la misma pila HTTP del bridge (undici):

| Request | HTTP |
| --- | --- |
| `http://localhost:7456/api/active` | **403** |
| `http://127.0.0.1:7456/api/active` | **200** |

No es transitorio: el 403 depende solo del alias de loopback usado. Con el daemon en `0.0.0.0`,
el alias correcto es `127.0.0.1`.

### Fix aplicado

`/home/mattias/.config/opencode/opencode.json` → mcp `open-design` → `--daemon-url`

```
- http://localhost:7456
+ http://127.0.0.1:7456
```

JSON validado. Reinicio de OpenCode hecho por el usuario; MCP verificado operativo después.

## 2. Decisión de destino

Proyecto **nuevo** en OpenDesign, para no confundirlo con los existentes
(`Soporte V2`, `idea soporte`, `soporte-v2-starbucks-local`).

Nombre propuesto: **`Soporte Redesign 2.x`** (id `soporte-redesign-2x`).

Motivo: el plan exige textualmente *"No modificar, borrar, copiar ni escribir archivos del
proyecto de OpenDesign"* y *"OpenDesign permanece intacto y se usa únicamente como guía"*.
Escribir en `Soporte V2` contradiría ese alcance.

## 3. Pasos tras el reinicio

1. `create_project(name="Soporte Redesign 2.x", id="soporte-redesign-2x")`
2. `collect_brief(artifactType="product-prototype", projectTitle="Soporte Redesign 2.x", locale="es")`
   — dejar que el usuario complete la tarjeta; reutilizar `confirm_brief` para el brief legible.
3. `list_agents` → elegir runtime **solo** de la lista devuelta (no adivinar claude/codex/opencode).
4. `start_run(project="soporte-redesign-2x", prompt=<abajo>, requestId=<UUID estable>)`
5. `get_run(runId)` cada 30–60 s. Runs típicos: 5–30 min. **No cancelar** ni sustituir con
   `write_file`: la espera es el agente pensando, no un cuelgue.
6. Al terminar: `previewUrl`. Solo si se necesita editar código fuente → `get_artifact`.

## 4. Prompt del run (derivado del plan de auditoría)

### Dirección

Rebuild visual del frontend de Soporte Técnico hacia una sola gramática cálida. Conservar
contratos: URLs, permisos, DTOs/API, SignalR, batch y exportaciones. No introducir Tailwind v4.

### Tokens (fuente de verdad: `frontend/src/app/globals.css`)

```
--color-page-bg:#f2f0eb  --color-surface:#ffffff  --color-surface-warm:#edebe9
--color-cream:#faf6ee    --color-text:rgba(0,0,0,.87)  --color-text-secondary:#33433d
--color-muted:rgba(0,0,0,.58)  --color-house:#1e3932  --color-accent:#00754a
--color-accent-deep:#006241    --color-gold:#cba258   --color-border:#d6dbde
--color-border-soft:#e7e7e7    --color-danger:#c82014
--color-success-surface:#e6f4ea --color-warning-surface:#fff7e0 --color-error-surface:#fdecea
--container-max:1440px  --sidebar-width:272px  --sidebar-collapsed:76px
--space-page-x:16/24/40px  --space-section:18px
--radius-control:5px  --radius-card:12px  --radius-large:16px  --radius-pill:9999px
--shadow-card:0 0 .5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)
--shadow-popover:0 8px 28px rgba(0,0,0,.12)
--focus-ring:0 0 0 3px rgba(0,117,74,.35)
```

Verde profundo = estructura. Verde acción = CTA/éxito. Dorado = **solo** fuera de turno/mock.
Rojo = **solo** error/peligro.

### Shell

```
[anuncio opcional, ocupa espacio real]
├── Sidebar 272px (colapsado 76px, drawer <900px + scrim)
└── Page band: eyebrow / título / descripción / badges
    Page main max 1440px
    └── [flujo|filtros|tabla 1fr] + [aside sticky 360px desde 1100px]
```

### Principios

- Una gramática visual para login, shell, páginas, chat, toasts y overlays.
- Menos tarjetas: separadores y espacio negativo para agrupaciones no seleccionables.
- Un page band por página; no duplicar hero dentro de componentes.
- Datos siempre con valor, unidad, rango/fuente y alternativa legible sin color.
- Estados disabled / hover / focus-visible / active; hit area mínima 44px.
- Motion solo para cambio de estado; animar `transform`/`opacity`, nunca `width`/`height`.
  Respetar reduced motion.

### Contratos de dominio que el prototipo debe respetar

- Medios exactos: `Interno`, `Presencial`, `WhatsApp`, `E-ticket`.
- Categorías exactas: `Audio/Video`, `Cuentas/Accesos`, `Hardware`, `Impresión`, `Otros`,
  `Redes/Conectividad`, `Sistemas académicos`, `Software`.
- `FueraDeTurno` lo calcula el servidor: mostrarlo de solo lectura, nunca como input.
- Jerarquía por IDs (`GrupoPadre` → `Grupo` → `Area`); `Area.GrupoId` puede ser `null`.
- No presentar `systemView`, `estado` ni `fuente` como campos persistidos de `Atencion`.

### Pantallas a cubrir

`/` · `/dashboard` (consolidados en una sola fuente de filtros) · `/soporte` · `/reporte` ·
`/horarios` · `/perfil/[id]` · login · overlays (banner, chat, toasts, modales, tarjeta-detalle).

## 5. No hacer

- No escribir en el proyecto `Soporte V2` ni en `idea soporte`.
- No borrar componentes locales legacy (`AtencionTable`, `DashboardCards`, `DashboardStats`)
  ni los `*V2`: consolidar solo tras verificar imports y regresiones.
- No sustituir un `start_run` en curso por `write_file`.
- No ejecutar la implementación local sin aprobación explícita y créditos.

## 6. Resultado

### Segundo bloqueador encontrado y resuelto

El primer `start_run` (runId `5612d2c0`) murió en **312 ms**:

```
ld-linux-x86-64.so.2: cannot load /usr/local/bin/opencode (deleted): No such file or directory
```

Causa: `/usr/local/bin/opencode` dentro del contenedor es un **bind mount de un archivo**, no de un
directorio, anclado al inodo del 9-Sep. El host reemplazó `opencode.exe` el 14-Sep (actualización) →
el contenedor apuntaba a un inodo borrado.

| | inodo | fecha |
| --- | --- | --- |
| Host `/home/mattias/.nvm/.../opencode-ai/bin/opencode.exe` | 4739048 | Sep 14 18:10 |
| Contenedor `/usr/local/bin/opencode` | 4360322 | Sep 9 13:59 |

Fix: `docker restart open-design-open-design-1` (compose, `project=open-design`, no Coolify).
Tras el restart el inodo coincide y `opencode --version` → `1.18.31`.

### Tercer bloqueador: prompt con referencia externa

El segundo run (runId `8fa47471`) salió `exit 0` pero con `deliverableValidation: "no_artifact"`.
El agente intentó leer el proyecto de referencia y el sandbox lo rechazó:

```
permission requested: external_directory (/app/.od/projects/soporte-v2-starbucks-local/*); auto-rejecting
```

3 de 7 tool calls fallidas, todas lecturas externas. **El sandbox impide a un run leer fuera de su
propio directorio de proyecto.** El prompt debe ser autosuficiente: no referenciar otros proyectos
de OpenDesign ni el repo local.

### Run final

`start_run` runId **`8714cc9b-a659-4f47-9816-901f317426ec`** · agent `opencode` ·
skill `redesign-existing-projects` · designSystem `starbucks` ·
requestId `f2302444-0778-4b2d-8fa6-6dce693a6a8e` · **309 s** · 18 tool calls (17 ok, 1 fallida).

`status: succeeded` · `deliverableValid: true` · `deliverableValidation: "valid"` ·
`entryFile: index.html` · 7 artefactos:

`index.html` (entrada + Dashboard) · `login.html` · `soporte.html` · `reporte.html` ·
`horarios.html` · `perfil.html` · `overlays.html` · más `styles/tokens.css`, `styles/app.css`, `js/app.js`.

### Verificación en navegador real (Playwright)

- `index.html` carga, título `Soporte Técnico UPDS 2.x — Panel`. **0 errores y 0 warnings de consola.**
- Navegación por sidebar verificada end-to-end: click en "Soporte" → `soporte.html`
  (título `Soporte UPDS 2.x — Registrar atención`).
- Semántica correcta: `complementary "Navegación principal"`, `nav` con sección "Operación".

Comprobaciones por grep sobre los archivos:

| Comprobación | Resultado |
| --- | --- |
| 11 valores del contrato de dominio exactos | ✅ presentes |
| Hex hardcodeado fuera de `tokens.css` | ✅ **cero** |
| Rastro de Tailwind | ✅ ninguno |
| Emojis operativos (U+1F300+) | ✅ ninguno (solo dingbats: `✓`, `☰`, `✎`) |

Conforme al plan en los puntos duros: shell 272px, page band único, badge **dorado solo** para
"fuera de turno · calculado por servidor", KPIs con valor + unidad + rango + fuente, y el modal
"Solo contexto · NO PERSISTIDO / Campos mock" que etiqueta `Sistema` y `Estado` como mock con su
"fuente real" explícita.

### Pendiente

- Los links `previewUrl` / `studioUrl` mueren al reiniciar el daemon: pedir `get_run(runId)` de nuevo.
- La implementación local en `frontend/` sigue sin autorizar (DoD del plan: aprobación + créditos).
- El proyecto de referencia `Soporte V2` no fue tocado.

