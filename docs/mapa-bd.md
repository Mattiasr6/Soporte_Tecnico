# Mapa de la base de datos — `postgres-dev`

> Levantado el 2026-09-20 contra la BD de desarrollo: `postgresql+psycopg://…@localhost:5433/soporte`
> (`backend-fastapi/.env` → `DATABASE_URL`). Todo lo de abajo salió de consultas de solo lectura.
>
> **Caveat:** esto es la BD **dev**. Si la v1/producción es otra instancia, los números cambian y hay
> que dar acceso de lectura para mapearla igual.

---

## 1. Inventario de tablas

Hay 8 tablas en `public`. El backend Python mapea solo 6.

| Tabla | Filas | ¿La usa Python? | Qué es |
|---|---:|---|---|
| `Atenciones` | 1957 | ✅ `app/models/atencion.py` | el hecho: un ticket/atención |
| `Usuarios` | 10 | ✅ `app/models/usuario.py` | 7 técnicos, 2 jefes, 1 auxiliar |
| `Areas` | 53 | ✅ `app/models/area.py` | área solicitante (3er nivel) |
| `Grupos` | 4 | ✅ `app/models/grupo.py` | 2do nivel |
| `GruposPadres` | 3 | ✅ `app/models/grupo_padre.py` | 1er nivel (raíz) |
| `Horarios` | 13 | ✅ `app/models/horario.py` | turnos por usuario/mes |
| `__EFMigrationsHistory` | 2 | ❌ | legado .NET (Entity Framework) |
| `alembic_version` | 1 | ❌ (la usa alembic) | `0001_baseline` |

**No hay tablas fantasma.** Lo "fantasma" no está en el esquema, está en las **filas** (§6).

### Linaje de migraciones

- `__EFMigrationsHistory` (backend .NET, v1/v2):
  - `20260716153907_InitialPostgres` → EF Core 8.0.11, el baseline del 2026-07-16
  - `20260828080203_V2_JerarquiaAreas` → EF Core 8.0.0, la que **agregó la jerarquía** (`GrupoPadreId`, `GrupoId`, `AreaId`) el 2026-08-28
- `alembic_version` → `0001_baseline` (el proyecto Python solo declaró baseline; no migró nada todavía)

---

## 2. `Atenciones` — 17 columnas

| Columna | Tipo | Nulo | Qué es |
|---|---|---|---|
| `Id` | int | NO | PK |
| `UsuarioId` | int | NO | FK `Usuarios` → técnico que atendió |
| `AreaSolicitante` | varchar | NO | **texto legacy** (nombre libre del área) |
| `MedioSolicitud` | varchar | NO | Interno / Presencial / WhatsApp / E-ticket |
| `UsuarioSolicitante` | varchar | NO | **código de tipo**: ADM, BEC, DOC, EST, EIAG |
| `Categoria` | varchar | NO | una de las 8 categorías válidas |
| `Descripcion` | varchar | NO | el problema, texto libre |
| `Solucion` | varchar | NO | la solución, texto libre |
| `Observaciones` | varchar | SÍ | |
| `EnlaceApoyo` | varchar | SÍ | |
| `ColaboradorId` | int | SÍ | FK `Usuarios` → segundo técnico |
| `FueraDeTurno` | bool | NO | |
| `FechaRegistro` | date | NO | **sin hora** |
| `CreatedAt` | timestamptz | NO | fecha de carga al sistema, no del incidente |
| `GrupoPadreId` | int | SÍ | FK `GruposPadres` — **nivel 1** |
| `GrupoId` | int | SÍ | FK `Grupos` — **nivel 2** |
| `AreaId` | int | SÍ | FK `Areas` — **nivel 3** |

**Dato clave:** conviven el texto viejo (`AreaSolicitante`) y la jerarquía nueva (3 FKs **nullable**).
Que sean nullable es lo que permite que existan filas sin clasificar.

Índices: `FechaRegistro`, `UsuarioId`, `ColaboradorId`, `AreaId`, `GrupoId`, `GrupoPadreId` + PK.

---

## 3. Cómo trabaja el backend Python con la jerarquía

Al crear una atención (`POST /api/atenciones` y `/batch`):

1. Si viene `area_id` → resuelve `(grupo_padre_id, grupo_id, area_id, nombre)` desde `Areas`.
2. Si viene `grupo_id` → resuelve `(grupo_padre_id, grupo_id, None, nombre)`.
3. Si solo viene **texto** `area_solicitante` → busca ese nombre **exacto** en `Areas`:
   - lo encuentra → completa la jerarquía
   - **no lo encuentra → guarda la fila con los 3 IDs en `NULL`** ← *esta es la causa de las 25 filas sin clasificar*
4. Si no viene ni texto ni IDs → error 400: *"Debe enviar area_solicitante o grupo_padre_id/grupo_id/area_id"*.

**Conclusión: mientras alguien escriba un área que no exista en el catálogo, van a seguir naciendo filas sin jerarquía.** El saneo de datos no alcanza si no se cierra esa puerta (validar en el formulario / crear el área).

Catálogos que el backend valida:
- **Categorías (8, cerrado)** — `app/services/categorias.py`: `Audio/Video`, `Cuentas/Accesos`, `Hardware`, `Impresión`, `Otros`, `Redes/Conectividad`, `Sistemas académicos`, `Software`
- **Estados** — `PATCH /api/usuarios/estado` (`app/routers/usuarios.py`) solo acepta `disponible` y
  `ocupado`; `ausente` se rechaza a propósito ("No puedes cambiarte a ausente manualmente").
  Valores almacenados posibles en `Usuarios.EstadoActual`: `Disponible`, `Ocupado`, `Ausente`, `Extraturno`.
  El estado **mostrado** lo calcula `estado_efectivo()` (`app/services/estados.py`): si estás
  Disponible/Ocupado pero la hora actual cae **fuera del horario del mes**, se muestra **extraturno**
  automáticamente; si no hay horario cargado para ese mes, se respeta el estado tal cual.
  → *Consecuencia: como `Horarios` no tiene septiembre (§7), hoy nadie puede figurar como "fuera de turno" automático.*
- **Medios**: texto libre de 50 chars (no validado)

---

## 4. Catálogo de jerarquía

3 grupos-padres → 4 grupos → 53 áreas.

| Padre | Id | Atenciones | Grupos que cuelgan |
|---|---:|---:|---|
| Administrativos | 1 | 1572 | Investigación, Rectorado, Vicerrectorado |
| Extras | 3 | 226 | Eventos |
| Académicos | 2 | 134 | — |

| Grupo | Id | Padre | Atenciones |
|---|---:|---|---:|
| Vicerrectorado | 3 | Administrativos | 332 |
| Investigación | 1 | Administrativos | 74 |
| Rectorado | 2 | Administrativos | 62 |
| Eventos | 4 | Extras | 12 |

**53 áreas**: 17 cuelgan de un grupo (480 atenciones) y 36 cuelgan directo del padre (1452).
Eso es correcto, no un error: hay áreas que no pasan por un grupo.

**2 áreas huérfanas** (0 atenciones): `Sala 2 (Directorio)` (id 50) y `Sala 3 (Directorio)` (id 51), ambas bajo Extras.

---

## 5. Estado de los datos

Rango: **2026-01-05 → 2026-09-01**.

| Mes | Total | Sin área | Sin grupo |
|---|---:|---:|---:|
| 2026-01 | 200 | 0 | 160 |
| 2026-02 | 199 | 0 | 165 |
| 2026-03 | 155 | 0 | 114 |
| 2026-04 | 141 | 0 | 90 |
| 2026-05 | 214 | 0 | 138 |
| 2026-06 | 275 | 0 | 196 |
| 2026-07 | 419 | 0 | 325 |
| 2026-08 | 336 | **7** | 271 |
| 2026-09 | 18 | **18** | 18 |
| **Total** | **1957** | **25** | 1477 |

Lo limpio:
- **Categorías: 0 fantasmas.** Las 8 que existen en la BD son exactamente las 8 válidas (1957 filas repartidas entre las 8).
- Enero–julio: **0 filas sin área** (el backfill de `V2_JerarquiaAreas` las cubrió todas).

Lo sucio:
- **25 filas sin jerarquía** (7 del 2026-08-31 + 18 del 2026-09-01) → §6.
- **`AreaSolicitante` tiene 97 textos distintos** pero solo se usan **51 áreas** del catálogo: el mismo área se escribió con variantes históricas. La FK es el camino limpio; el texto no.
- **56 filas** comparten `fecha + área + categoría + descripción` (grupos de 2 y 3). Puede ser legítimo (3 personas pidiendo lo mismo el mismo día) o copia-pega — hay que revisarlo, no lo toqué.
- `Horarios`: **no hay turnos de septiembre** (solo mes 7 y mes 8 de 2026).

---

## 6. El corte: las 25 filas sin jerarquía

**No son datos fantasma duplicados.** Verifiqué cada una de las 18 de septiembre contra el resto de la
tabla: **0 coincidencias** de descripción y **0 de solución**. Son incidentes reales, escritos de verdad
("Cable de red no conecta bien en Internacional", "Se le cambió el cable"). Lo único que les falta es la
clasificación.

De los 14 textos distintos que usan esas 25 filas, **11 ya existen en el catálogo** (backfill directo) y **3 no existen** (requieren decisión):

| Texto en `AreaSolicitante` | Filas | ¿En catálogo? | Área | Padre |
|---|---:|---|---:|---|
| EIAG | 6 | ✅ | 46 | Extras |
| Directorio | 3 | ✅ | 44 | Extras |
| Marketing | 2 | ✅ | 14 | Administrativos |
| Relaciones Públicas | 2 | ✅ | 19 | Administrativos |
| Sistemas | 2 | ✅ | 23 | Administrativos |
| Vicerrectorado | 2 | ✅ | 42 | Administrativos |
| Bienestar Estudiantil | 1 | ✅ | 7 | Administrativos |
| Coordinación Acad. FCS | 1 | ✅ | 11 | Administrativos |
| Recepción | 1 | ✅ | 17 | Administrativos |
| Servicios Generales | 1 | ✅ | 22 | Administrativos |
| Vicerrectorado Administrativo | 1 | ✅ | 27 | Administrativos |
| **Aula A-05** | 1 | ❌ | — | — |
| **Aula B-01** | 1 | ❌ | — | — |
| **Laboratorios y gabinetes de Medicina** | 1 | ❌ | — | — |

Los 3 sin catálogo son **aulas/laboratorios**, no oficinas. `Aula A-05` y `Aula B-01` parecen aulas
sueltas (¿crear un área "Aulas"? ¿o mapearlas a Laboratorios?). `Laboratorios y gabinetes de Medicina`
parece un área real que simplemente **nunca se cargó al catálogo**.

Para ubicarlas:

```sql
select "Id", "FechaRegistro", "AreaSolicitante", "Categoria"
from "Atenciones"
where "AreaId" is null
order by "FechaRegistro", "Id";
```

---

## 7. Horarios — 10 columnas

`Id`, `UsuarioId`, `Label`, `HoraInicio1`, `HoraFin1`, `HoraInicio2`, `HoraFin2`, `Mes`, `Anio`, `CreatedAt`.

Turno **por usuario y por mes**, con hasta **dos franjas** (turno partido: `09:00-15:00 + 18:00-20:00`).
Las 13 filas: 7 de julio 2026 + 6 de agosto 2026. **Septiembre vacío.**
`HoraInicio`/`HoraFin` guardan `'HH:MM'` como texto, no como hora.

---

## 8. Qué significa "sanear septiembre"

Orden propuesto, de menor a mayor riesgo:

1. **Backfill de las 22 filas** cuyo texto ya existe en el catálogo → `UPDATE` de `AreaId`, y de ahí
   `GrupoId`/`GrupoPadreId` siguiendo `Areas` (§6, tabla).
2. **Decisión sobre las 3 sin catálogo**: crear las áreas faltantes o mapearlas a una existente.
3. **Cerrar la puerta**: que el formulario de "nueva atención" no deje guardar sin área (el dashboard ya
   asume que el 100% está clasificado y hoy muestra 25 en el limbo).
4. **Revisar las 56 duplicadas** (decisión tuya: son legítimas o hay que deduplicar).
5. **Cargar los turnos de septiembre** si corresponden.

> ⚠️ Los puntos 1, 2 y 5 **escriben** en la BD. Sobre producción eso es irreversible: hay que hacer
> **backup antes**, y conviene ensayar el `UPDATE` en dev primero. El backup es tu decisión, no lo hago solo.

---

## 9. Pendiente de verificar

- Si la v1/producción es **otra** instancia (no esta dev), todo lo de arriba es solo dev: hay que repetir
  el levantamiento allá y comparar (sobre todo el conteo de septiembre y si el corte es el mismo 2026-09-01).
- Si el `AreaSolicitante` de producción tiene más variantes que las 97 de dev.
