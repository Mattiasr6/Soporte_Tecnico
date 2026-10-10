"""One-off cutover move of the old Soporte lab data onto the horarios tables.

Sources (read only): `Laboratorios`, `LabAtenciones` (+ `LabCategorias`) and
the auxiliar JSON files in the data dir (`equipo_auxiliares.json`,
`horarios_auxiliares.json`, `horarios_sabados.json`). `LabPcs`, `Software*`
and `Novedades` are only counted: if they hold rows they go to the report.

Targets: `horarios.atenciones`, `horarios.perfiles` (rol auxiliar/encargado
and turno_habitual only), and the G6 Saturday plan (`sabados`,
`sabado_horarios`, `rotacion_sabados`). No login account or perfil is ever
created: an unmatched person is reported and the original name is kept in
the migrated text.

Idempotency: every migrated attention and Saturday is recorded in
`horarios.migracion_origen`, so re-running skips it. Perfil updates only
fill or promote values, so they converge on their own.

Triggers: the inserts satisfy them instead of bypassing them (no
`session_replication_role`). `creado_en`/`turno`/`auxiliar_id` are passed
explicitly (an empty source turno is left NULL so `trg_atenciones_turno`
derives it from `creado_en`), and a PC that is not `operativa` is not linked
(`trg_atenciones_pc_activa` would refuse a non-correctivo attention on it).

With `aplicar=False` nothing is written: the plan is computed from reads only.
"""

import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, text

LA_PAZ = ZoneInfo("America/La_Paz")
ORIGEN_ATENCION = "LabAtenciones"
ORIGEN_SABADO = "horarios_sabados.json"

# Soporte turno names (Django) → horarios codes; keys are normalized.
TURNOS = {"manana": "M", "mediodia": "MD", "tarde": "T", "noche": "N"}
# LabCategorias → horarios tipo. G7 limits template tipos to these four
# (correctivo and cambio_estado need a PC flow the old records never had).
TIPOS = {
    "software": "programas",
    "soporte en laboratorios": "docente",
    "soporte academico": "personal",
    "hardware": "preventivo",
    "red e internet": "preventivo",
    "infraestructura": "preventivo",
    "seguridad": "preventivo",
    "inventario": "preventivo",
    "reporte y gestion": "preventivo",
}
TIPO_POR_DEFECTO = "preventivo"
# Soporte "labs" that are not rooms: their attentions keep ambiente NULL.
LABS_OMITIDOS = {"soporte"}
TABLAS_SIN_DESTINO = ("LabPcs", "Software", "SoftwareLab", "PcSoftware", "Novedades")

DESCRIPCION_MAX = 500
SOLUCION_MAX = 1000
NOTA_SABADO_MAX = 200


@dataclass(frozen=True)
class Incidencia:
    seccion: str
    origen_id: str
    motivo: str
    detalle: str


@dataclass
class Resultado:
    aplicado: bool
    conteos: Counter[str] = field(default_factory=Counter)
    incidencias: list[Incidencia] = field(default_factory=list)

    def reportar(self, seccion: str, origen_id: Any, motivo: str, detalle: Any) -> None:
        self.incidencias.append(
            Incidencia(
                seccion, str(origen_id), motivo, "" if detalle is None else str(detalle)
            )
        )


def normalizar(valor: str | None) -> str:
    """Lowercase, no accents, single spaces: how names and codes are compared."""
    sin_tildes = unicodedata.normalize("NFKD", valor or "")
    plano = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", plano).strip().lower()


def _clave_tokens(valor: str) -> str:
    # "Mercado Bejarano Mabel" and "Mabel Mercado Bejarano" are the same person.
    return " ".join(sorted(normalizar(valor).split()))


class Personas:
    """Find a perfil by full name or email (perfil or its Soporte account)."""

    def __init__(self, conn: Connection) -> None:
        self.perfiles: dict[str, dict[str, Any]] = {}
        self._claves: dict[str, set[str]] = {}
        self._usuarios_sin_perfil: set[str] = set()
        filas = conn.execute(
            text(
                "select p.id::text as id, p.nombre_completo, p.correo, p.rol, "
                'p.turno_habitual, u."DisplayName" as nombre_usuario, u."Email" as correo_usuario '
                'from horarios.perfiles p left join "Usuarios" u on u."Id" = p.usuario_id'
            )
        ).mappings()
        for fila in filas:
            self.perfiles[fila["id"]] = dict(fila)
            for valor in (
                fila["nombre_completo"],
                fila["correo"],
                fila["nombre_usuario"],
                fila["correo_usuario"],
            ):
                for clave in self._claves_de(valor):
                    self._claves.setdefault(clave, set()).add(fila["id"])
        for fila in conn.execute(
            text(
                'select u."DisplayName", u."Email" from "Usuarios" u where not exists '
                '(select 1 from horarios.perfiles p where p.usuario_id = u."Id")'
            )
        ):
            for valor in fila:
                self._usuarios_sin_perfil.update(self._claves_de(valor))

    @staticmethod
    def _claves_de(valor: str | None) -> set[str]:
        if not valor or not valor.strip():
            return set()
        return {normalizar(valor), _clave_tokens(valor)}

    def buscar(self, nombre: str) -> tuple[str | None, str]:
        """Return (perfil id, "") or (None, reason)."""
        for clave in (normalizar(nombre), _clave_tokens(nombre)):
            ids = self._claves.get(clave)
            if ids and len(ids) == 1:
                return next(iter(ids)), ""
            if ids:
                return None, "auxiliar_ambiguo"
        if self._claves_de(nombre) & self._usuarios_sin_perfil:
            return None, "usuario_sin_perfil"
        return None, "auxiliar_sin_perfil"


def _recortar(texto: str, maximo: int) -> tuple[str, bool]:
    if len(texto) <= maximo:
        return texto, False
    return texto[: maximo - 1].rstrip() + "…", True


def _ya_migrados(conn: Connection, origen: str) -> set[str]:
    return set(
        conn.execute(
            text("select origen_id from horarios.migracion_origen where origen = :o"),
            {"o": origen},
        ).scalars()
    )


def _registrar(
    conn: Connection, origen: str, origen_id: str, destino: str, destino_id: str
) -> None:
    conn.execute(
        text(
            "insert into horarios.migracion_origen (origen, origen_id, destino, destino_id) "
            "values (:o, :oi, :d, :di)"
        ),
        {"o": origen, "oi": origen_id, "d": destino, "di": destino_id},
    )


def _mapear_laboratorios(conn: Connection, res: Resultado) -> dict[int, int | None]:
    ambientes = conn.execute(
        text("select id, codigo, nombre from horarios.ambientes")
    ).all()
    por_codigo = {normalizar(a.codigo): a.id for a in ambientes}
    por_nombre = {normalizar(a.nombre): a.id for a in ambientes if a.nombre}
    mapa: dict[int, int | None] = {}
    for lab in conn.execute(
        text('select "Id", "Codigo", "Nombre" from "Laboratorios" order by "Id"')
    ):
        res.conteos["laboratorios"] += 1
        if normalizar(lab.Codigo) in LABS_OMITIDOS:
            mapa[lab.Id] = None
            res.reportar(
                "laboratorios",
                lab.Id,
                "laboratorio_omitido",
                f"{lab.Codigo} · {lab.Nombre}",
            )
            continue
        ambiente = por_codigo.get(normalizar(lab.Codigo)) or por_nombre.get(
            normalizar(lab.Nombre)
        )
        mapa[lab.Id] = ambiente
        if ambiente is None:
            res.reportar(
                "laboratorios",
                lab.Id,
                "laboratorio_sin_ambiente",
                f"{lab.Codigo} · {lab.Nombre}",
            )
        else:
            res.conteos["laboratorios_con_ambiente"] += 1
    return mapa


def _creado_en(
    creado: datetime | None, fecha: date, inicio_turno: time | None
) -> datetime:
    """Keep the original timestamp when it falls on FechaRegistro (La Paz day,
    or UTC day: Django stamped late-night rows with the UTC date). A row
    typed in later for an earlier day gets FechaRegistro at its turno start
    (noon without turno), so day and turno stay right in the dashboards."""
    if creado is not None and fecha in (
        creado.astimezone(LA_PAZ).date(),
        creado.astimezone(UTC).date(),
    ):
        return creado
    return datetime.combine(fecha, inicio_turno or time(12), LA_PAZ)


def _resolver_auxiliares(
    src: Any, res: Resultado, personas: Personas
) -> tuple[list[str], bool]:
    """Split "A + B + C" into perfil ids (first = author, rest = colaboradores);
    every unmatched name is reported. Returns (ids, some name unmatched)."""
    auxiliares: list[str] = []
    sin_perfil = False
    for nombre in (n.strip() for n in (src["AuxiliarNombre"] or "").split("+")):
        if not nombre:
            continue
        perfil, motivo = personas.buscar(nombre)
        if perfil is None:
            sin_perfil = True
            res.reportar("atenciones", src["Id"], motivo, nombre)
        elif perfil not in auxiliares:
            auxiliares.append(perfil)
    return auxiliares, sin_perfil


def _completar_auxiliar(
    conn: Connection, res: Resultado, src: Any, destino: int, personas: Personas
) -> None:
    """Re-run after the missing perfiles were created: an attention migrated
    without author gets it now (only while auxiliar_id is still NULL)."""
    auxiliares, _ = _resolver_auxiliares(src, res, personas)
    if not auxiliares:
        return
    res.conteos["atenciones_auxiliar_completado"] += 1
    if res.aplicado:
        conn.execute(
            text(
                "update horarios.atenciones set auxiliar_id = cast(:a as uuid), "
                "resuelto_por = coalesce(resuelto_por, cast(:a as uuid)), "
                "colaboradores = cast(:c as uuid[]) where id = :i and auxiliar_id is null"
            ),
            {"a": auxiliares[0], "c": auxiliares[1:], "i": destino},
        )


def _migrar_atenciones(
    conn: Connection, res: Resultado, labs: dict[int, int | None], personas: Personas
) -> None:
    ya = _ya_migrados(conn, ORIGEN_ATENCION)
    horas = _horarios_turno(conn)
    sin_autor = {
        f.origen_id: f.id
        for f in conn.execute(
            text(
                "select m.origen_id, a.id from horarios.migracion_origen m "
                "join horarios.atenciones a on a.id::text = m.destino_id "
                "where m.origen = :o and a.auxiliar_id is null"
            ),
            {"o": ORIGEN_ATENCION},
        )
    }
    pcs = {
        (p.ambiente_id, normalizar(p.etiqueta)): (p.id, p.estado)
        for p in conn.execute(
            text("select id, ambiente_id, etiqueta, estado from horarios.ambiente_pcs")
        )
    }
    filas = conn.execute(
        text(
            'select a.*, c."Nombre" as categoria, l."Codigo" as lab_codigo '
            'from "LabAtenciones" a left join "LabCategorias" c on c."Id" = a."CategoriaId" '
            'left join "Laboratorios" l on l."Id" = a."LaboratorioId" order by a."Id"'
        )
    ).mappings()
    for src in filas:
        oid = str(src["Id"])
        res.conteos["atenciones_origen"] += 1
        if oid in ya:
            res.conteos["atenciones_ya_migradas"] += 1
            if oid in sin_autor:
                _completar_auxiliar(conn, res, src, sin_autor[oid], personas)
            continue
        fila = _armar_atencion(src, res, labs, personas, pcs, horas)
        res.conteos["atenciones_nuevas"] += 1
        if not res.aplicado:
            continue
        nuevo = conn.execute(
            text(
                "insert into horarios.atenciones (ambiente_id, pc_id, tipo, descripcion, "
                "solucion, estado, auxiliar_id, resuelto_por, resuelto_en, creado_en, "
                "actualizado_en, turno, medio_solicitud, colaboradores, detalles) values "
                "(:ambiente_id, :pc_id, :tipo, :descripcion, :solucion, 'resuelto', "
                "cast(:auxiliar_id as uuid), cast(:auxiliar_id as uuid), :creado_en, "
                ":creado_en, :creado_en, :turno, :medio, cast(:colaboradores as uuid[]), "
                "cast(:detalles as jsonb)) returning id"
            ),
            fila,
        ).scalar_one()
        _registrar(conn, ORIGEN_ATENCION, oid, "horarios.atenciones", str(nuevo))


def _armar_atencion(
    src: Any,
    res: Resultado,
    labs: dict[int, int | None],
    personas: Personas,
    pcs: dict[tuple[int, str], tuple[int, str]],
    horas: dict[str, tuple[time, time]],
) -> dict[str, Any]:
    oid = src["Id"]
    nota: list[str] = []

    ambiente_id = labs.get(src["LaboratorioId"])
    if ambiente_id is None:
        res.conteos["atenciones_sin_ambiente"] += 1
        nota.append(f"Lab: {src['lab_codigo'] or src['LaboratorioId']}")
        res.reportar("atenciones", oid, "laboratorio_sin_ambiente", src["lab_codigo"])

    pc_id = None
    pc_nombre = (src["PcNombre"] or "").strip()
    if pc_nombre:
        pc = pcs.get((ambiente_id, normalizar(pc_nombre))) if ambiente_id else None
        if pc and pc[1] == "operativa":
            pc_id = pc[0]
        else:
            motivo = "pc_no_operativa" if pc else "pc_sin_match"
            res.conteos[f"atenciones_{motivo}"] += 1
            nota.append(f"PC: {pc_nombre}")
            res.reportar("atenciones", oid, motivo, pc_nombre)

    auxiliares, sin_perfil = _resolver_auxiliares(src, res, personas)
    if sin_perfil:
        res.conteos["atenciones_auxiliar_sin_perfil"] += 1
        nota.append(f"Auxiliar: {src['AuxiliarNombre'].strip()}")

    categoria = src["categoria"] or ""
    tipo = TIPOS.get(normalizar(categoria))
    if tipo is None:
        tipo = TIPO_POR_DEFECTO
        res.reportar("atenciones", oid, "categoria_sin_tipo", categoria)

    turno_src = normalizar(src["Turno"])
    turno = TURNOS.get(turno_src)
    if turno is None:
        # NULL lets trg_atenciones_turno derive it from creado_en.
        res.conteos["atenciones_turno_derivado"] += 1
        if turno_src:
            res.reportar("atenciones", oid, "turno_desconocido", src["Turno"])

    medio_src = normalizar(src["MedioSolicitud"])
    medio = "WhatsApp" if medio_src == "whatsapp" else "Presencial"
    if medio_src not in ("", "whatsapp", "presencial"):
        res.reportar("atenciones", oid, "medio_desconocido", src["MedioSolicitud"])

    descripcion = (src["Descripcion"] or "").strip()
    if len(descripcion) < 3:
        descripcion = "Atención migrada sin descripción"
        res.reportar("atenciones", oid, "descripcion_vacia", src["Descripcion"])
    if nota:
        marca = "[Migrado] " + " · ".join(nota)
        cuerpo, cortado = _recortar(descripcion, DESCRIPCION_MAX - len(marca) - 1)
        descripcion = f"{cuerpo}\n{marca}"
    else:
        descripcion, cortado = _recortar(descripcion, DESCRIPCION_MAX)
    if cortado:
        res.reportar("atenciones", oid, "descripcion_recortada", src["Descripcion"])

    solucion = (src["Solucion"] or "").strip()
    observaciones = (src["Observaciones"] or "").strip()
    if observaciones:
        solucion = f"{solucion}\nObservaciones: {observaciones}".strip()
    solucion, cortado = _recortar(solucion, SOLUCION_MAX)
    if cortado:
        res.reportar("atenciones", oid, "solucion_recortada", "")

    creado_en = _creado_en(
        src["CreatedAt"],
        src["FechaRegistro"],
        horas[turno][0] if turno in horas else None,
    )
    if creado_en != src["CreatedAt"]:
        res.conteos["atenciones_fecha_de_registro"] += 1
        res.reportar(
            "atenciones", oid, "hora_ajustada_a_fecha_registro", src["CreatedAt"]
        )

    detalles = {
        "migracion": {
            "origen": ORIGEN_ATENCION,
            "id": oid,
            "laboratorio": src["lab_codigo"],
            "categoria": categoria,
            "auxiliar": src["AuxiliarNombre"],
            "pc": pc_nombre or None,
            "turno": src["Turno"],
            "fuera_de_turno": bool(src["FueraDeTurno"]),
            "fecha_registro": src["FechaRegistro"].isoformat(),
            "creado": src["CreatedAt"].isoformat() if src["CreatedAt"] else None,
        }
    }
    return {
        "ambiente_id": ambiente_id,
        "pc_id": pc_id,
        "tipo": tipo,
        "descripcion": descripcion,
        "solucion": solucion or None,
        "auxiliar_id": auxiliares[0] if auxiliares else None,
        "colaboradores": auxiliares[1:],
        "creado_en": creado_en,
        "turno": turno,
        "medio": medio,
        "detalles": json.dumps(detalles, ensure_ascii=False),
    }


def _leer_json(data_dir: Path, nombre: str, res: Resultado) -> Any:
    ruta = data_dir / nombre
    if not ruta.is_file():
        res.reportar("archivos", nombre, "archivo_ausente", str(ruta))
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def _turno_de(clave: str) -> str | None:
    return TURNOS.get(normalizar(clave))


def _migrar_equipo(
    conn: Connection, data_dir: Path, res: Resultado, personas: Personas
) -> None:
    """Promote/demote auxiliar ↔ encargado as the Django roster says. Other
    roles (tecnico, admin…) are never changed: a mismatch is only reported."""
    datos = _leer_json(data_dir, "equipo_auxiliares.json", res) or {}
    for aux in datos.get("auxiliares", []):
        nombre = (aux.get("nombre") or "").strip()
        res.conteos["equipo_personas"] += 1
        perfil_id, motivo = personas.buscar(nombre)
        if perfil_id is None:
            res.conteos["equipo_sin_perfil"] += 1
            res.reportar("equipo", nombre, motivo, nombre)
            continue
        perfil = personas.perfiles[perfil_id]
        deseado = "encargado" if aux.get("encargado") else "auxiliar"
        if perfil["rol"] == deseado:
            continue
        if perfil["rol"] not in ("auxiliar", "encargado"):
            res.reportar(
                "equipo",
                nombre,
                "rol_distinto",
                f"perfil {perfil['rol']}, Django {deseado}",
            )
            continue
        res.conteos["perfiles_actualizados"] += 1
        perfil["rol"] = deseado
        if res.aplicado:
            conn.execute(
                text(
                    "update horarios.perfiles set rol = :r where id = cast(:i as uuid)"
                ),
                {"r": deseado, "i": perfil_id},
            )


def _horarios_turno(conn: Connection) -> dict[str, tuple[time, time]]:
    return {
        f.turno: (f.hora_inicio, f.hora_fin)
        for f in conn.execute(
            text("select turno, hora_inicio, hora_fin from horarios.horarios_turno")
        )
    }


def _hora(valor: Any) -> time | None:
    try:
        return time.fromisoformat(str(valor))
    except ValueError:
        return None


def _migrar_turnos(
    conn: Connection, data_dir: Path, res: Resultado, personas: Personas
) -> None:
    """Fill turno_habitual from the Django weekly roster (never overwrite)."""
    datos = _leer_json(data_dir, "horarios_auxiliares.json", res) or {}
    horas = _horarios_turno(conn)
    vistos: set[str] = set()
    for clave, bloque in datos.items():
        turno = _turno_de(clave)
        if turno is None:
            res.reportar("turnos", clave, "turno_desconocido", clave)
            continue
        actual = horas.get(turno)
        propio = (_hora(bloque.get("inicio")), _hora(bloque.get("fin")))
        if actual and propio != actual:
            res.reportar(
                "turnos",
                turno,
                "horario_turno_distinto",
                f"{bloque.get('inicio')}-{bloque.get('fin')}",
            )
        for nombre in bloque.get("auxiliares", []):
            perfil_id, motivo = personas.buscar(nombre)
            if perfil_id is None:
                res.conteos["turnos_sin_perfil"] += 1
                res.reportar("turnos", turno, motivo, nombre)
                continue
            if perfil_id in vistos:
                res.reportar("turnos", turno, "turno_duplicado", nombre)
                continue
            vistos.add(perfil_id)
            perfil = personas.perfiles[perfil_id]
            if perfil["turno_habitual"] == turno:
                continue
            if perfil["turno_habitual"] is not None:
                res.reportar(
                    "turnos",
                    turno,
                    "turno_distinto",
                    f"{nombre}: perfil {perfil['turno_habitual']}",
                )
                continue
            res.conteos["perfiles_actualizados"] += 1
            perfil["turno_habitual"] = turno
            if res.aplicado:
                conn.execute(
                    text(
                        "update horarios.perfiles set turno_habitual = :t where id = cast(:i as uuid)"
                    ),
                    {"t": turno, "i": perfil_id},
                )


def _plan_sabado(
    clave: str,
    turnos: dict[str, Any],
    res: Resultado,
    personas: Personas,
    horas: dict[str, tuple[time, time]],
) -> tuple[dict[str, str], list[tuple[str, time, time]], list[str]]:
    """One Django date → (perfil → turno, own hours, unmatched names)."""
    asignados: dict[str, str] = {}
    horas_propias: list[tuple[str, time, time]] = []
    sin_perfil: list[str] = []
    for clave_turno, bloque in turnos.items():
        turno = _turno_de(clave_turno)
        if turno is None or turno == "N":
            res.reportar("sabados", clave, "turno_no_valido_sabado", clave_turno)
            continue
        inicio, fin = _hora(bloque.get("inicio")), _hora(bloque.get("fin"))
        if inicio and fin and fin > inicio and (inicio, fin) != horas.get(turno):
            horas_propias.append((turno, inicio, fin))
        for nombre in bloque.get("auxiliares", []):
            perfil_id, motivo = personas.buscar(nombre)
            if perfil_id is None:
                sin_perfil.append(nombre)
                res.reportar("sabados", clave, motivo, nombre)
            elif perfil_id in asignados:
                res.reportar("sabados", clave, "auxiliar_en_dos_turnos", nombre)
            else:
                asignados[perfil_id] = turno
    return asignados, horas_propias, sin_perfil


def _asignar_sabado(conn: Connection, fecha: date, asignados: dict[str, str]) -> None:
    for perfil_id, turno in asignados.items():
        conn.execute(
            text(
                "insert into horarios.rotacion_sabados (fecha, auxiliar_id, turno) "
                "values (:f, cast(:a as uuid), :t) on conflict (fecha, auxiliar_id) do nothing"
            ),
            {"f": fecha, "a": perfil_id, "t": turno},
        )


def _migrar_sabados(
    conn: Connection, data_dir: Path, res: Resultado, personas: Personas
) -> None:
    """Django Saturday plan → G6 shape. A date already planned in horarios
    (not by this script) is left alone and reported; unmatched names go to the
    date note. On a re-run, a migrated date that still exists gets the people
    whose perfil was created since (existing assignments are kept)."""
    datos = _leer_json(data_dir, ORIGEN_SABADO, res) or {}
    ya = _ya_migrados(conn, ORIGEN_SABADO)
    planificados = {
        str(f)
        for f in conn.execute(text("select fecha from horarios.sabados")).scalars()
    }
    existentes = {
        (str(f.fecha), str(f.auxiliar_id))
        for f in conn.execute(
            text("select fecha, auxiliar_id from horarios.rotacion_sabados")
        )
    }
    horas = _horarios_turno(conn)
    for clave in sorted(datos):
        res.conteos["sabados_origen"] += 1
        try:
            fecha = date.fromisoformat(clave)
        except ValueError:
            res.reportar("sabados", clave, "fecha_invalida", clave)
            continue
        if fecha.weekday() != 5:
            res.reportar("sabados", clave, "no_es_sabado", clave)
            continue
        migrado = clave in ya
        if migrado and clave not in planificados:
            res.conteos["sabados_ya_migrados"] += 1  # cleared in horarios since
            continue
        if not migrado and clave in planificados:
            res.reportar(
                "sabados",
                clave,
                "sabado_ya_planificado",
                "no se toca el plan de horarios",
            )
            continue
        asignados, horas_propias, sin_perfil = _plan_sabado(
            clave, datos[clave], res, personas, horas
        )
        if migrado:
            res.conteos["sabados_ya_migrados"] += 1
            asignados = {
                p: t for p, t in asignados.items() if (clave, p) not in existentes
            }
            res.conteos["sabados_asignaciones"] += len(asignados)
            if res.aplicado:
                _asignar_sabado(conn, fecha, asignados)
            continue
        nota = None
        if sin_perfil:
            nota, _ = _recortar(
                "Migrado sin perfil: " + ", ".join(sin_perfil), NOTA_SABADO_MAX
            )
        res.conteos["sabados_nuevos"] += 1
        res.conteos["sabados_asignaciones"] += len(asignados)
        if not res.aplicado:
            continue
        conn.execute(
            text("insert into horarios.sabados (fecha, nota) values (:f, :n)"),
            {"f": fecha, "n": nota},
        )
        for turno, inicio, fin in horas_propias:
            conn.execute(
                text(
                    "insert into horarios.sabado_horarios (fecha, turno, hora_inicio, hora_fin) "
                    "values (:f, :t, :i, :h)"
                ),
                {"f": fecha, "t": turno, "i": inicio, "h": fin},
            )
        _asignar_sabado(conn, fecha, asignados)
        _registrar(conn, ORIGEN_SABADO, clave, "horarios.sabados", clave)


def _contar_sin_destino(conn: Connection, res: Resultado) -> None:
    for tabla in TABLAS_SIN_DESTINO:
        if (
            conn.execute(
                text("select to_regclass(:t)"), {"t": f'public."{tabla}"'}
            ).scalar()
            is None
        ):
            continue
        total = int(conn.execute(text(f'select count(*) from "{tabla}"')).scalar_one())
        res.conteos[f"{tabla}_filas"] = total
        if total:
            res.reportar(
                "sin_destino",
                tabla,
                "filas_no_migradas",
                f"{total} filas: revisar a mano",
            )


def migrar(conn: Connection, data_dir: Path, aplicar: bool) -> Resultado:
    """Run the whole move on `conn`. The caller owns the transaction: commit
    after an applied run, roll back otherwise."""
    res = Resultado(aplicado=aplicar)
    personas = Personas(conn)
    labs = _mapear_laboratorios(conn, res)
    _migrar_atenciones(conn, res, labs, personas)
    _migrar_equipo(conn, data_dir, res, personas)
    _migrar_turnos(conn, data_dir, res, personas)
    _migrar_sabados(conn, data_dir, res, personas)
    _contar_sin_destino(conn, res)
    return res


def escribir_reporte(res: Resultado, ruta: Path) -> Path:
    """Write the review report: `.json` (counts + rows) or CSV (rows only)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    filas = [vars(i) for i in res.incidencias]
    if ruta.suffix.lower() == ".json":
        contenido = {
            "aplicado": res.aplicado,
            "conteos": dict(res.conteos),
            "incidencias": filas,
        }
        ruta.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return ruta
    with ruta.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(
            f, fieldnames=["seccion", "origen_id", "motivo", "detalle"]
        )
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta
