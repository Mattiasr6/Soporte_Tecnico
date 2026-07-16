# Pipeline: 

## Phase: spec

---
title: "Mejora formulario registro de atenciones (/soporte)"
status: "approved"
version: "1.0"
priority: "alta"
estimated_effort: "1 día"
dependencies: []
---

## Historia de usuario

> Como **técnico de soporte**, quiero **mejorar el formulario de registro de atenciones** para **evitar errores de captura (áreas fantasmas, categorías inválidas) y tener una experiencia de uso más limpia y profesional**.

## Objetivo

Refactorizar el formulario de registro de atenciones (`AtencionTable.tsx`): convertir el área solicitante a un combobox restringido, agregar 2 nuevos tipos de usuario solicitante, corregir el placeholder de categoría, y rediseñar la UI a un layout profesional con etiquetas visibles y mejor jerarquía visual.

---

## Stack Tecnológico (OBLIGATORIO)

| Capa | Tecnología | Versión | Notas |
|------|-----------|---------|-------|
| Frontend | React / Next.js (App Router) | 14 | `"use client"` |
| Estilos | Tailwind CSS | v3/v4 | Slate/Amber theme existente |
| Backend | ASP.NET Core | 8 | Minimal changes |
| ORM | Entity Framework Core | 8 | Solo validación, sin migraciones |
| BD | PostgreSQL | - | No se toca esquema |
| Auth | JWT Bearer | - | Ya implementado |

---

## Arquitectura

### Diagrama de componentes

```
[Browser: AtencionTable.tsx]
    ├── [Componente interno: AreaCombobox] --reemplaza--> [AreaAutocomplete.tsx]
    ├── [<select> Medio solicitud]
    ├── [<select> Usuario solicitante (5 opciones)]
    ├── [<select> Categoria (placeholder disabled)]
    ├── [<input> Descripcion + sugerencias]
    ├── [<input> Solucion]
    ├── [Toggle: Obs + Enlace + Colaborador]
    └── --HTTP POST--> [API: /api/atenciones/batch] --> [PostgreSQL: Atenciones]
```

### Mapa de archivos

```
# Archivos a MODIFICAR (frontend):
frontend/src/components/AtencionTable.tsx
  - Reemplazar AreaAutocomplete por AreaCombobox interno
  - Cambiar USUARIOS_SOL a 5 opciones
  - Categoría: placeholder disabled
  - Rediseño UI completo (labels, espaciado, jerarquía)
  - Validación: categoría obligatoria, área debe existir

# Archivos a ELIMINAR (frontend):
frontend/src/components/AreaAutocomplete.tsx
  - Se elimina por completo (reemplazado por AreaCombobox inline)

# Archivos a MODIFICAR (backend):
backend/SoporteTecnico.API/Controllers/AtencionesController.cs
  - Línea 358: validación CSV import: aceptar "EST" y "EIAG"
```

---

## Contratos de Datos

### AtencionCreateDto (sin cambios)

```typescript
interface AtencionCreate {
  areaSolicitante: string;    // Debe existir en getAreas()
  medioSolicitud: string;     // "Interno" | "Presencial" | "WhatsApp" | "E-ticket"
  usuarioSolicitante: string; // "ADM" | "BEC" | "DOC" | "EST" | "EIAG"
  categoria: string;          // Requerida, en CategoriasValidas
  descripcion: string;        // Requerida
  solucion: string;           // Requerida
  observaciones?: string;     // Opcional
  enlaceApoyo?: string;       // Opcional
  colaboradorId?: number;     // Opcional
  fechaRegistro: string;      // ISO date
}
```

### Modelo BD (sin cambios)

```sql
-- No se modifican tablas. Solo consultas SELECT a Atenciones existentes y POST batch.
```

### Frontend — Estados de UI del formulario

| Estado | Condición | Render |
|--------|-----------|--------|
| Loading | `saving === true` | Botón guardar con spinner + disabled |
| Error | Error en `createAtenciones()` | Toast error con mensaje |
| Success | Atenciones guardadas | Toast éxito + reset a fila en blanco |
| ValidationError | Campos obligatorios faltantes | Botón guardar disabled + count 0 |
| Empty | Sin tickets (nunca ocurre, siempre hay 1 blank row) | Una fila en blanco lista para llenar |

---

## Flujo Principal

1. Usuario ve el formulario con una fila en blanco (o navega entre tickets existentes via dots/anterior/siguiente)
2. Usuario completa campos en orden:
   a. **Área solicitante**: escribe para filtrar, selecciona de la lista desplegable (o Tab para autocomplete)
   b. **Medio solicitud**: selecciona de dropdown
   c. **Usuario solicitante**: selecciona de dropdown (ADM/BEC/DOC/EST/EIAG)
   d. **Categoría**: selecciona de dropdown (placeholder "Seleccionar categoría..." no seleccionable)
   e. **Descripción**: escribe, recibe sugerencias de autocompletado desde atenciones previas
   f. **Solución**: escribe
3. Usuario puede expandir opcionales: Observaciones, Enlace de apoyo, Colaborador
4. Usuario hace clic en "Guardar atenciones"
5. Sistema valida en frontend:
   - `areaSolicitante` no vacío y existe en áreas cargadas
   - `descripcion` y `solucion` no vacíos
   - `categoria` no vacía
6. Sistema envía POST `/api/atenciones/batch`
7. Backend valida categorías y usuario solicitante
8. Backend inserta registros y devuelve `{ registrosInsertados: N }`
9. Frontend muestra toast éxito y resetea formulario

### Flujo Alternativo — Navegación multi-ticket

1. Usuario hace clic en "Agregar fila"
2. Se agrega un nuevo ticket en blanco
3. Dots de navegación muestran cantidad total + posición actual
4. Usuario navega entre tickets con dots, "Anterior" y "Siguiente"
5. Cada ticket mantiene su estado independiente
6. Al guardar, se envían TODOS los tickets válidos en un solo POST batch

### Flujo de Error — Validación

| Condición | Respuesta | UI |
|-----------|-----------|-----|
| Área no seleccionada / fantasma | Validación frontend | Botón guardar disabled (validCount 0) |
| Categoría vacía | Validación frontend | Botón guardar disabled |
| Categoría inválida | Backend 400 | Toast error "Categorías inválidas: X" |
| Descripción vacía | Validación frontend | Botón guardar disabled |
| Solución vacía | Validación frontend | Botón guardar disabled |
| Error de red/servidor | Backend 500 | Toast error (catch genérico) |

---

## Catálogo de Errores

| Código | HTTP | Condición | Mensaje visible | Log |
|--------|------|-----------|----------------|-----|
| ERR-001 | 400 | Categoría inválida | "Categorías inválidas: X" | warn |
| ERR-002 | 400 | Lista vacía | "La lista de atenciones está vacía" | warn |
| ERR-003 | 500 | Error interno servidor | "Error al guardar" (catch) | error |
| ERR-004 | Frontend | Área no existe en lista | Botón guardar disabled, no se puede enviar | - |
| ERR-005 | Frontend | Categoría vacía | Botón guardar disabled | - |

---

## Reglas de Negocio

1. **RN-01 — Área obligatoria y existente:** El campo área solicitante SOLO acepta valores que existan en el array devuelto por `getAreas()`. No se permite texto libre. El combobox bloquea valores no listados.
2. **RN-02 — Usuario solicitante:** Solo 5 valores válidos: `ADM`, `BEC`, `DOC`, `EST`, `EIAG`. Backend debe aceptar los 5 en validación CSV (línea 358).
3. **RN-03 — Categoría obligatoria:** El placeholder "Seleccionar categoría..." no es un valor seleccionable. El option debe tener `disabled` (HTML nativo).
4. **RN-04 — Campos obligatorios para guardar:** `areaSolicitante`, `descripcion`, `solucion`, `categoria`, `medioSolicitud`, `usuarioSolicitante`. Opcionales: `observaciones`, `enlaceApoyo`, `colaboradorId`.
5. **RN-05 — Datos preservados:** No se modifica esquema BD, no hay migraciones. Solo cambios en frontend + validación backend mínima.

---

## Criterios de Aceptación (Gherkin)

```gherkin
Feature: Formulario de registro de atenciones mejorado

  Background:
    Given un técnico logueado en /soporte
    And existen 59 áreas precargadas en el sistema

  Scenario: Área solicitante — combobox restringido
    Given el campo "Área solicitante"
    When el usuario escribe "Siste"
    Then se muestra dropdown con "Sistemas" y áreas que contengan "Siste"
    When el usuario presiona Tab
    Then se autocompleta con "Sistemas"
    When el usuario intenta escribir "AreaFalsa"
    And no existe en la lista
    Then al hacer blur (o al guardar) el valor se rechaza
    And el campo se muestra como inválido

  Scenario: Categoría — placeholder no seleccionable
    Given el select de categoría
    When el usuario abre el dropdown
    Then "Seleccionar categoría..." aparece como texto decorativo
    And no puede seleccionarse como valor
    When el usuario no selecciona ninguna categoría
    Then el botón guardar está disabled

  Scenario: Usuario solicitante — 5 opciones
    Given el select de usuario solicitante
    Then tiene exactamente 5 opciones: ADM, BEC, DOC, EST, EIAG

  Scenario: Guardar atenciones exitoso
    Given todos los campos obligatorios completados
    When el usuario hace clic en "Guardar atenciones (N)"
    Then se envía POST /api/atenciones/batch
    And se muestra toast de éxito
    And el formulario se resetea a una fila en blanco

  Scenario: UI profesional — layout con labels
    Given el formulario de atenciones
    Then cada campo tiene un label visible arriba
    And los campos están bien espaciados
    And es responsive (1 columna mobile, mejor espaciado desktop)
    And la navegación entre tickets funciona con dots + anterior/siguiente
```

---

## Mockups ASCII

```
┌──────────────────────────────────────────┐
│  ⚡ Plantillas rápidas                    │
│  [Conectividad] [Impresora] [PC no enciende] ... │
│                                          │
│  ● ● ○ ○ ○    Ticket 1 de 3              │
│                                          │
│  ┌─ Área solicitante ──────────────────┐ │
│  │ Sistemas                          ▼│ │
│  └────────────────────────────────────┘ │
│  ┌─ Medio ───────┐ ┌─ Usuario ────────┐ │
│  │ Interno     ▼│ │ ADM            ▼│ │
│  └────────────────┘ └──────────────────┘ │
│  ┌─ Categoría ─────────────────────────┐ │
│  │ Seleccionar categoría...          ▼│ │
│  └────────────────────────────────────┘ │
│  ┌─ Descripción ───────────────────────┐ │
│  │ Sin acceso a internet...           │ │
│  └────────────────────────────────────┘ │
│  ┌─ Solución ──────────────────────────┐ │
│  │ Se reinicio switch...              │ │
│  └────────────────────────────────────┘ │
│                                          │
│  [+1h] [Colaborador: ▼] [Obs] [Link]    │
│                                          │
│  ← Anterior         Siguiente →          │
│                                          │
│  [+ Agregar fila]    [✓ Guardar (1)]     │
└──────────────────────────────────────────┘
```

---

## Especificación Técnica Detallada

### 1. AreaCombobox — Restricción a valores existentes

**Qué cambia:**
- Se elimina `AreaAutocomplete.tsx` (115 líneas, portal-based)
- Se crea un componente inline en `AtencionTable.tsx` que funciona como combobox restringido

**Comportamiento:**
- Input text que filtra la lista de áreas mientras el usuario escribe
- Downshift-style: flechas arriba/abajo navegan opciones, Enter selecciona, Escape cierra
- **Tab completa automáticamente** la opción más cercana (primer match del filtro actual)
- Si el usuario escribe algo que NO coincide exactamente con un área (case-insensitive), al perder el foco (blur) se REVIERTE al último valor válido o se limpia
- El dropdown se muestra como lista flotante (no portal, posición absoluta local)
- Estilo visual consistente con el resto del formulario

**Estados:**
| Estado | Visual |
|--------|--------|
| Vacio | Placeholder "Buscar área..." |
| Escribiendo | Dropdown se abre con opciones filtradas |
| Match exacto | Input muestra el área, dropdown cerrado |
| Sin match | Input muestra texto, dropdown muestra "Sin resultados" o vacío |
| Blur sin match | Input se revierte al último valor válido o se limpia |

**Pseudocódigo:**
```
onChange:
  setFilter(value)
  setOpen(true)
  if areas.includes(value) → accept value
  else → clear selection flag

onBlur:
  if value not in areas → revert to lastValidValue or ""

onKeyDown Tab:
  if open and filtered.length > 0 → select first filtered item
  setOpen(false)

onKeyDown Enter:
  if open and filtered.length > 0 → select highlighted item

onKeyDown Escape:
  setOpen(false)

onKeyDown ArrowDown/ArrowUp:
  navigate highlightIndex
```

### 2. USUARIOS_SOL — 5 opciones

```typescript
const USUARIOS_SOL = ["ADM", "BEC", "DOC", "EST", "EIAG"];
```

**Backend** — en `AtencionesController.cs` línea 358 (CSV import):
```csharp
// Cambiar de:
UsuarioSolicitante = usuarioSol is "ADM" or "BEC" or "DOC" ? usuarioSol : "ADM",
// A:
UsuarioSolicitante = usuarioSol is "ADM" or "BEC" or "DOC" or "EST" or "EIAG" ? usuarioSol : "ADM",
```

### 3. Categoría — placeholder disabled

```tsx
<select value={row.categoria} onChange={...}>
  <option value="" disabled>Seleccionar categoría...</option>
  {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
</select>
```

### 4. Rediseño UI — layout profesional con labels

**Estructura por ticket:**
```
[Label] ──────────────────────
  [Campo]
```

**Layout:**
- Cada campo tiene un `<label>` de texto arriba (text-sm, font-medium, text-slate-300)
- Inputs con borde más definido: `border-slate-600`, focus `ring-1 ring-amber-500`
- Grid de 2 columnas para pares lógicos: medio + usuario, descripción + solución (en desktop)
- Espaciado consistente entre grupos
- Toggle buttons (+1h, Obs, Link, Colaborador) en fila compacta
- Sección de navegación (dots + anterior/siguiente) centrada entre el contenido
- Botones "Agregar fila" y "Guardar" al fondo, lado a lado

**Etiquetas visibles:**
```
Área solicitante | Medio de solicitud | Usuario solicitante | Categoría
Descripción      | Solución aplicada
```

**Estilos base (manteniendo paleta existente):**
- Fondo tarjeta: `bg-slate-800/60 border border-slate-700/50 rounded-xl`
- Inputs: `bg-slate-900 border-slate-600 text-slate-100`
- Labels: `text-xs font-medium text-slate-400 uppercase tracking-wider`
- Focus: `ring-1 ring-amber-500/50 border-amber-500`
- Botón primario (Guardar): `bg-amber-500 text-slate-900 font-bold`
- Dots navegación: `h-2 rounded-full`, activo `bg-amber-500 w-6`, inactivo `bg-slate-600 w-2`

---

## Orden de Implementación (Sisyphus)

1. **Backend — validación EST/EIAG** (`AtencionesController.cs:358`)
   - Una línea: agregar `or "EST" or "EIAG"` al pattern match del CSV import
2. **Frontend — AreaCombobox** (`AtencionTable.tsx`)
   - Reemplazar import + uso de `AreaAutocomplete` con combobox inline restringido
   - Implementar lógica de filtro + selección forzada + Tab autocomplete + blur revert
3. **Frontend — USUARIOS_SOL + placeholder categoría** (`AtencionTable.tsx`)
   - Agregar "EST" y "EIAG" a la constante
   - Agregar `disabled` al option placeholder de categoría
4. **Frontend — Rediseño UI** (`AtencionTable.tsx`)
   - Agregar labels visibles sobre cada campo
   - Reorganizar layout con grid responsive
   - Mejorar espaciado, jerarquía visual, consistencia
5. **Frontend — Eliminar** `AreaAutocomplete.tsx`
   - Una vez confirmado que no se usa en ningún otro lado

---

## Lo que NO está en alcance (explícito)

- ❌ No se modifican modelos de BD ni migraciones EF Core
- ❌ No se tocan otros componentes (HistorialModal, ToggleButton, AuthProvider)
- ❌ No se agregan nuevos endpoints al backend
- ❌ No se modifica la funcionalidad de sugerencias de descripción (se mantiene igual)
- ❌ No se cambian las plantillas rápidas (PLANTILLAS)
- ❌ No se agregan roles de usuario nuevos
- ❌ No se toca el dashboard ni estadísticas

## Definition of Done (DoD)

1. [ ] AreaCombobox: solo permite seleccionar áreas existentes en `getAreas()`. Texto libre se rechaza al blur.
2. [ ] Tab completa el área filtrando automáticamente.
3. [ ] USUARIOS_SOL tiene 5 opciones: `["ADM", "BEC", "DOC", "EST", "EIAG"]`.
4. [ ] Backend (`AtencionesController.cs:358`) acepta las 5 opciones en import CSV.
5. [ ] Placeholder de categoría tiene `disabled` y no es seleccionable.
6. [ ] Categoría es obligatoria (si está vacía, botón guardar disabled).
7. [ ] Layout del formulario tiene labels visibles sobre cada campo.
8. [ ] Formulario es responsive: 1 columna mobile, mejor espaciado en desktop.
9. [ ] Navegación entre tickets funciona (dots + anterior/siguiente).
10. [ ] `AreaAutocomplete.tsx` eliminado del proyecto.
11. [ ] Build frontend: `npm run build` exitoso (0 errors, 0 warnings).
12. [ ] Build backend: `dotnet build` exitoso.
13. [ ] No hay `as any`, `@ts-ignore` ni type suppressions nuevas.
14. [ ] Datos existentes en BD intactos (no hay migraciones ni cambios de esquema).
