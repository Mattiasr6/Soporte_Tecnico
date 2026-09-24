# Import histórico — decisiones cerradas

> Insumo para la spec. Todo lo de abajo fue decidido por el usuario y verificado contra las
> fuentes reales. Nada queda abierto.
> Fecha: 2026-09-24 · Rama: `dev`

## Origen

Dos exports de Excel (Google Sheets) de técnicos **retirados en 2026** que nunca usaron el
software. Su trabajo se registraba en una planilla compartida.

| Archivo (`docs/csv/`) | Técnico | Filas | Encoding | Delimitador |
|---|---|---|---|---|
| `Atención al Cliente - Soporte técnico(Gabriel).csv` | Gabriel Torrico | 364 | ISO-8859 (latin-1) | `;` |
| `Atención al Cliente - Soporte técnico(Deymar).csv` | Deymar Lozano | 193 | ISO-8859 (latin-1) | `;` |

- **557 filas** de datos. El resto de las líneas del archivo están **vacías** (relleno del export):
  hay que filtrar por `ID` no vacío.
- Los **IDs son de cada archivo** (1..N), no son globales. No se usan.
- **No hay columna de técnico** — el técnico es el dueño del archivo.
- **No hay `FueraDeTurno` ni `CreatedAt`.**
- **No hay cruces entre los dos archivos.**

### Columnas del origen

`ID · Fecha · Área solicitante · Usuario Solicitante (ADM/BEC) · Medio de Solicitud · Categoría Incidente · Descripción / detalle · Solución / acciones · Observaciones · Enlace de Apoyo`

Fecha en `DD/MM/YYYY`. `N/A` y `''` en `Observaciones`/`Enlace` significan "vacío".

## Usuarios a crear

| Email | Nombre | Role | Login |
|---|---|---|---|
| `Gabriel.Torrico@upds.edu.bo` | Gabriel Torrico | `Tecnico` | **no** |
| `Deymar.Lozano@upds.edu.bo` | Deymar Lozano | `Tecnico` | **no** |

Se dan de baja pero **conservan sus atenciones a nombre propio**.

## Normalizaciones

| Qué | De | A | Filas |
|---|---|---|---|
| Fecha | `15/01/2025` | `15/01/2026` | 8 (Deymar) |
| Fecha | `21/01/1900` | `21/01/2026` | 1 (Deymar) |
| Fecha | `19/03/2002` | `19/03/2026` | 1 (Deymar) |
| Medio | `Correo` | `Interno` | 1 (Deymar) |

Verificado: **todas las fechas quedan entre 2026-01 y 2026-04**, ningún mes ≥ mayo.

## Correcciones a nivel fila

El área de origen quedó mal copiada en 3 filas; la descripción/solución dice el área real.

| Archivo | ID | Área en CSV | Área real | Motivo |
|---|---|---|---|---|
| Deymar | 50 | `EIAG` | `SFIC` | solución: "impresoras compartidas en **SFCI**" |
| Gabriel | 201 | `ADM` | `Académicos Modular` | descripción: "SSID De **Lab-Procesos**" |
| Gabriel | 287 | `Presencial` | `Cardio Salud` | descripción: "Registro De Activos En **Cardio Salud**" |

## Filas descartadas

| Archivo | ID | Motivo |
|---|---|---|
| Gabriel | 363 | duplicado real: ID consecutivo al 362, **todos** los campos idénticos |

**556 filas se cargan** (557 − 1).

## Duplicados revisados (no se descartan)

6 grupos con misma `(Fecha, Área, Descripción)`. Veredicto del usuario:

| Grupo | Veredicto |
|---|---|
| `15/01 EIAG "Impresora Compartida"` ×2 | 2 reales — van a áreas distintas (`SFIC` y `EIAG`) |
| `27/01 Marketing "Verificacion cuentas Saads"` ×2 | 2 reales — PCs distintas (Priscila Arau / Noelia Schenn) |
| `16/01 MKT "Saads Lento…"` ×3 | **3 reales** — mismo lugar, equipos distintos |
| `26/01 Vicerrectorado "Ingresar Al SAADS"` ×2 | 2 reales — un equipo de ADM, otro de un BEC |
| `10/03 Medicina "Proyectar"` ×2 | 2 reales — soluciones distintas |
| `14/04 Docente "SSID UpdsDocentes"` ×2 | **1 sola** (→ filas descartadas) |

## Mapeo de áreas sin resolver

46 textos de origen que no resuelven contra el catálogo. Destino decidido:

### Grupo A — typos y variantes (64 filas)

| Origen | Destino |
|---|---|
| `RRPP` | `Relaciones Públicas` |
| `Centro De Investigacion De Ingenieria`, `Centro de Investigacion de Ingenieria`, `centro De Investigacion De Ingenieria`, `Centro de Investigacion De Ingennieria`, `Centro de Invetsigacion De Ingenieria` | `C. de Inv./ Ingeniería` |
| `MKT`, `Marketing-Contabilidad` | `Marketing` |
| `Vicerrectorado Academico` | `Vicerrectorado` |
| `Rectorado regional`, `Rectorado Regional` | `Rectorado` |
| `Direcorio`, `Directoio` | `Directorio` |
| `Archivos` | `Archivo` |
| `CICS`, `Centro De Investigacion De Ciencias Sociales` | `C. de Inv./ C. Sociales` |
| `TTHH` | `Talento Humano` |
| `EAIG` | `EIAG` |
| `Datacenter` | `Data Center` |
| `Contailidad` | `Contabilidad` |
| `Sistmas` | `Sistemas` |
| `Vicerrectora` | `Vicerrectorado` |
| `Centro de Investigacion FCS` | `C. de Inv./ C. Salud` |

### Grupo B — decisiones de negocio (107 filas)

| Origen | Destino | Filas |
|---|---|---|
| `Docentes`, `Docente`, `Doecntes`, `Atencion Docente` | `Académicos Modular` | 33 |
| `Posgrado`, `Postgrado`, `Posgraado` | `EIAG` | 27 |
| `Medicina`, `Medicna` | `Académicos Semestral` | 23 |
| `CECYD`, `Cabina Cecyd` | `Extensión Universitaria` | 8 |
| `Internacionalizacion` | `EIAG` | 5 |
| `Enfermeria` | `Académicos Semestral` | 2 |
| `Sala Docentes` | `Sala de Docentes` | 2 |
| `Piso A`, `Campus` | `Académicos Modular` | 2 |
| `Caja y Registro` | `Caja` | 1 |
| `Asistente Rectorado` | `Rectorado` | 1 |
| `Rectorado Lic.Ynes` | `Rectorado` | 1 |
| `Coelgio Domingo Savio` | `Colegio Domingo Savio` (nueva) | 1 |
| `Constructora` | `Constructora` (nueva) | 1 |

Precedente de v1 usado para `Medicina` → `Académicos Semestral`:
`mapeo-areas.csv` ya tiene `Laboratorios y gabinetes de Medicina → Académicos Semestral`
y `Laboratorios de Computo → Académicos Modular`.

## Áreas nuevas de catálogo

3 áreas nuevas, **directas del sector `Extras`** (sin dependencia, `grupo` vacío, `activo=1`),
igual que `EIAG` que también es empresa aparte:

| Nombre | Sector | Grupo |
|---|---|---|
| `Colegio Domingo Savio` | `Extras` | (vacío) |
| `Constructora` | `Extras` | (vacío) |
| `Cardio Salud` | `Extras` | (vacío) |

## Verificado contra el sistema real

- Las 24 áreas que sí resuelven hoy se dejan como están.
- Los conjuntos cerrados del destino: `Medio` ∈ {Presencial, Interno, WhatsApp, E-ticket};
  `Usuario Solicitante` ∈ {ADM, BEC, DOC, EST}; las 8 categorías válidas. **Las 3 columnas ya
  cumplen** una vez normalizado `Correo`.
- El código de la `/jerarquia` (GUI) es el camino natural para crear las 3 áreas nuevas, o se
  agregan a los CSV de catálogo (`mapeo-areas-dedup.csv`).
- `mapeo-areas.csv` mapea **texto de origen → nombre canónico**, que es exactamente la forma de
  este problema; sumar las 46 filas ahí hace que el resolver existente
  (`construir_resolutor()` en `scripts/extraer_septiembre.py`) las tome sin código nuevo.
  ⚠️ Verificar que ninguna clave nueva pise una existente con otro destino.
- `seed_atenciones()` (en `scripts/seed.py`) es idempotente por `created_at` y **corta
  ruidosamente** si un área/técnico no existe. El origen **no trae `created_at`** → hay que
  sintetizarlo (hoy es la clave de idempotencia; ya es frágil: 53 colisiones en las 2214 reales).
