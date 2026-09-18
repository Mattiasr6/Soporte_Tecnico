# S4 — Import CSV

---
title: "S4 — Import CSV"
status: "approved"
version: "1.0"
priority: "media"
dependencies: ["S1", "S3"]
---

> **Como** técnico, **quiero** cargar atenciones históricas desde CSV con el mismo parseo de .NET,
> **para** migrar planillas sin perder datos.

**Objetivo:** paridad del `import-csv`, incluida resolución de jerarquía.

## Endpoint (`app/routers/atenciones.py`, mismo router)

| Método | Path | Body | Respuesta |
|--------|------|------|-----------|
| POST | `/api/atenciones/import-csv` | multipart `file` (.csv) | `{registros_insertados, errores[]\|null}` |

## Reglas

- **RN-S4-01:** encoding por BOM (UTF-8/UTF-16LE/BE), sin BOM → Latin1.
- **RN-S4-02:** salta header; requiere ≥8 columnas `;`; `parts[0]` no numérico → línea ignorada en silencio.
- **RN-S4-03:** mapeo fijo: `[1]` fecha, `[2]` área, `[3]` solicitante, `[4]` medio,
  `[5]` categoría, `[6]` descripción, `[7]` solución, `[8]` observaciones, `[9]` enlace.
- **RN-S4-04:** área/descripción/solución vacías → error de línea (no se inserta);
  categoría mala → `Otros` + error; medio fuera de `Presencial/Interno/WhatsApp/E-ticket` → `Interno`;
  solicitante fuera de `ADM/BEC/DOC/EST` → `ADM`; `N/A`/vacío → null; fecha mala → hoy UTC.
- **RN-S4-05:** **resuelve jerarquía por nombre** (área → grupo → padre, primer match);
  `fuera_de_turno` calculado en servidor.
- **RN-S4-06:** 0 filas válidas → 400 con `{error, errores}`.

## Catálogo de errores

| Código | Condición | HTTP |
|--------|-----------|------|
| ERR-S4-01 | sin archivo / vacío / no `.csv` | 400 |
| ERR-S4-02 | 0 válidos | 400 + errores[] |

## Archivos

```
backend-fastapi/app/services/csv_import.py  # detección encoding + parseo + validación (testeable puro)
backend-fastapi/app/routers/atenciones.py   # + endpoint (modifica)
backend-fastapi/tests/test_csv_import.py    # encodings, mapeos, defaults, errores, jerarquía
```

## Criterios de aceptación

- CSV Latin1 con ñ/tildes carga bien; UTF-8 con BOM también.
- Línea mala suma a `errores` sin tumbar el lote; lote todo-malo → 400.
- Área existente → FKs resueltas; área inexistente → FKs null pero se inserta con legacy.
- Filas de prueba marcadas `TEST-S4` y borradas; datos reales intactos.

## Definition of Done

1. [ ] endpoint verificado contra `postgres-dev` real
2. [ ] tests verdes · ruff + basedpyright limpios
3. [ ] Sin cambios fuera de `backend-fastapi/`

## Fuera de alcance

❌ Export CSV · ❌ UI de carga (S8).
