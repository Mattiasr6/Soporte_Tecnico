# Flujo de Soporte Técnico — wireframe de flujo

Diagramas del flujo core, previos a cualquier template. Fuente de verdad: los modelos
reales `Atencion` y `Horario` del backend y los controllers existentes
(`AuthController`, `AtencionesController`, `HorariosController`, `DashboardStats`).

> Etapa: **wireframe**. Valida estructura y jerarquía, no apariencia.
> El wireframe de pantallas vive en [`wireframes-pantallas.svg`](wireframes-pantallas.svg)
> y su fuente editable en [`wireframes-pantallas.excalidraw`](wireframes-pantallas.excalidraw).

---

## 1. Flujo core — de login a atención registrada

```mermaid
flowchart TD
    A([Abre la app]) --> B[Login: correo + contraseña]
    B --> C[Código de verificación 6 dígitos]
    C --> D{Rol}
    D -->|Jefe| E[Dashboard: resumen del equipo]
    D -->|Técnico| F[Panel del Técnico]

    F --> G[Marca estado propio]
    G --> H[Registra atención]
    H --> I[Área · Medio · Usuario · Categoría]
    I --> J[Descripción + Solución]
    J --> K{¿Fuera de turno?}
    K -->|Sí| L[marca fueraDeTurno]
    K -->|No| M[Colaborador opcional]
    L --> N[(Atencion guardada)]
    M --> N

    N --> O[Historial de Atenciones]
    E --> O
    O --> P[Jefe: estadísticas y comparativo]
```

Puntos que el wireframe deja visibles y conviene discutir antes de diseñar:

- **El rol decide la pantalla de entrada**, no un menú. `Jefe`/`canViewDashboard` → dashboard;
  cualquier otro → panel del técnico. ¿Es el comportamiento deseado, o el técnico necesita
  igualmente ver su resumen?
- **Área · Medio · Usuario · Categoría** son cuatro decisiones antes de escribir una sola letra
  del problema. Es el punto más caro del flujo.
- **Fuera de turno** y **Colaborador** son campos de clasificación, no de trabajo real.
  ¿Van en la fila principal o se revelan bajo "más opciones"?

---

## 2. Alta de horario (mes a mes)

```mermaid
flowchart LR
    Q([Técnico]) --> R[Elige mes y año]
    R --> S[Turno 1: hora inicio / fin]
    S --> T{¿Segundo turno?}
    T -->|Sí| U[Turno 2: hora inicio / fin]
    T -->|No| V[Guarda turno único]
    U --> W[(Horario: mes + anio)]
    V --> W
    W --> X[Se consulta desde Dashboard y perfil]
```

`Horario` admite dos turnos por día (`HoraInicio1/Fin1`, `HoraInicio2/Fin2`) y un `Label`
derivado. La pregunta de diseño: ¿el técnico edita **un mes completo** o **día por día**?
Un mes por pantalla cambia radicalmente la UI.

---

## 3. Secuencia — registrar una atención

```mermaid
sequenceDiagram
    participant T as Técnico
    participant F as Frontend
    participant A as API
    participant DB as PostgreSQL

    T->>F: Rellena la fila (área, categoría, descripción, solución)
    T->>F: Pulsa Guardar
    F->>A: POST /api/atenciones
    A->>A: Resuelve Area por FK (GrupoPadre → Grupo → Area)
    A->>DB: INSERT Atencion
    DB-->>A: id
    A-->>F: 201 Created
    F->>F: Toast + re-render de la tabla
    F-->>T: Fila confirmada
```

Nota de la v2: `Area` dejó de ser un string (`AreaSolicitante`) para ser una FK dentro de la
jerarquía `GrupoPadre → Grupo → Area`. El wireframe muestra un único selector "Área ▾";
**la UI real necesita o bien un selector en cascada de 3 niveles, o un combobox con búsqueda
sobre las 53 áreas.** Ese es el hallazgo principal de esta etapa — vale más que cualquier
decisión de color.

---

## Qué NO es esto

Sin color de marca, sin tipografía final, sin imágenes, sin estados de hover. Cualquier
decisión de apariencia se toma después, sobre el mockup, cuando este wireframe esté aprobado.

---

## Nota sobre el diagrama HTML

`flujo-soporte.html` **necesita scroll vertical** a 1440×900: mide 794px de alto contra un
presupuesto de ~770px. No es un defecto ajustable — con 5 lanes el diagrama no entra a
ningún ancho, ni siquiera a escala 1.0.

Se probaron y descartaron, sin perder información: ensanchar los nodos (viewBox 930→1186),
quitar las tres cards de conclusiones, y ocultar el legend. Ninguno alcanza.

Las salidas reales, si hace falta que entre en una pantalla:

| Opción | Costo |
|---|---|
| Fusionar Usuario → Frontend (4 lanes) | pierde la fila "Usuario"; necesita ancho ~1300, no verificado |
| Fusionar a 3 lanes | pierde dos filas de estructura |
| Partir en dos diagramas (Acceso / Registro) | pierde la vista de punta a punta |

Por ahora se acepta el scroll: el valor del diagrama está en la vista de punta a punta, y
recortar lanes cuesta más de lo que gana. La evidencia está en
`flujo-soporte.visual-check.json`.

En contraste, `registro-atencion.html` **sí encuadra** en los cuatro viewports — sirve de
referencia de la receta: viewBox ancho justo por debajo del techo de legibilidad, alto
ajustado al contenido, y sin cards.

