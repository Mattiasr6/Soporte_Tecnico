---
name: "migrations-ef-core-sin-perder-datos"
description: "Auto-generado: migracion, migration, cambiar modelo"
triggers:
  - "migracion"
  - "migration"
  - "cambiar modelo"
  - "ef core"
  - "entity framework"
  - "drop database"
  - "perder datos"
  - "--volumes"
  - "docker compose down"
  - "base de datos"
  - "migrations ef core sin perder datos"
tags:
  - "database"
  - "postgres"
  - "backend"
  - "efcore"
  - "docker"
  - "migrations"
  - "generated"
auto-generated: true
source: "meta-learner"
generated-at: "2026-07-16"
---
# Migraciones EF Core sin perder datos del equipo

## Regla de ORO

**NUNCA borrar el volumen de PostgreSQL del equipo.** Los datos de horarios, atenciones y usuarios son valiosos y no deben perderse.

## Lo que SÍ se puede hacer

### 1. Migraciones incrementales (seguro)
```bash
# 1. Modificar modelos en C#
# 2. Generar migracion
dotnet ef migrations add NombreDelCambio

# 3. Aplicar sin perder datos
dotnet ef database update
# o automaticamente via db.Database.Migrate() en Program.cs
```

### 2. Reset SOLO si no hay datos reales
Solo cuando:
- No hay data del equipo (proyecto recien clonado)
- Base local de desarrollo sin informacion valiosa
- El usuario explícitamente autoriza borrar

### 3. Para cambios breaking (que requieren transformacion de datos)
```csharp
// En Program.cs o en una migracion personalizada:
// 1. Agregar nueva columna
// 2. Migrar datos viejos a nueva columna
// 3. Eliminar columna vieja
// Todo en UNA migracion, sin drop
```

## Checklist pre-accion

- [ ] ¿Hay datos del equipo en esta BD? SI → **NO BORRAR**
- [ ] ¿El cambio requiere alterar schema? SI → migracion incremental
- [ ] ¿Es un cambio breaking? SI → preguntar al usuario antes
- [ ] ¿El usuario pidió explícitamente reiniciar BD? SINO → **NO BORRAR**

## Que hacer en vez de --volumes

```bash
# ❌ NUNCA: docker compose down --volumes
# ✅ SIEMPRE: docker compose down && docker compose up -d
# (sin --volumes preserva los datos)
```

