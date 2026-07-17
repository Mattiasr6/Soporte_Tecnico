---
name: "delegar-agente-corrector"
description: "Auto-generado: senior-web-developer, senior-web, senior-dotnet"
triggers:
  - "senior-web-developer"
  - "senior-web"
  - "senior-dotnet"
  - "senior-admin"
  - "subagent_type"
  - "delegar a"
  - "delegar agente corrector"
tags:
  - "sisyphus"
  - "delegacion"
  - "agentes"
  - "generated"
auto-generated: true
source: "meta-learner"
generated-at: "2026-07-17"
---
# Delegar al agente correcto - NO a Sisyphus-Junior

## Regla de ORO

Cuando el usuario pida explícitamente un subagente por nombre (ej: `@senior-web-developer`), **NUNCA** usar `category="..."`. 

## Lo correcto

### Si el usuario nombra un agente específico:
```typescript
// ✅ CORRECTO: usa subagent_type
task(
  subagent_type="senior-web-developer",
  load_skills=["..."],
  prompt="..."
)
```

### Si no hay agente específico:
```typescript
// Usar category SOLO si el usuario no pidio un agente concreto
task(
  category="web-frontend",
  ...
)
```

## Mapa de agentes (subagent_type vs category)

| El usuario dice | Usar |
|----------------|------|
| `@senior-web-developer` | `subagent_type="senior-web-developer"` |
| `@senior-dotnet-expert` | `subagent_type="senior-dotnet-expert"` |
| `@senior-admin` | `subagent_type="senior-admin"` |
| Categoria general (web, backend) | `category="web-frontend"` |

## Error común

```typescript
// ❌ MAL: Sisyphus-Junior recibe la tarea
task(category="web-frontend", load_skills=["senior-web"], prompt="...")

// ✅ BIEN: senior-web-developer recibe la tarea  
task(subagent_type="senior-web-developer", load_skills=["senior-web"], prompt="...")
```

**`category="web-frontend"`** mapea a **Sisyphus-Junior**, no a senior-web-developer.
**`subagent_type="senior-web-developer"`** mapea al agente correcto.

NUNCA confundir category (mapea a junior) con subagent_type (mapea al agente nombrado).

