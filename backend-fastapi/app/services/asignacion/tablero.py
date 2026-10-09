"""Lab traffic-light board and day timeline (ported from Django `lab_tablero_vista`
and `lab_timeline_vista`), as plain read queries over the horarios tables.

No new table and no SQL function: both are single SELECTs (the timeline is a
UNION ALL), so they live here and need no migration. Every source table is read
under fn_puede_ver elsewhere in the module, so both endpoints require the same.
Since G5 the timeline also lists lab novedades (`novedad`) and cierre decisions
(`cierre_validado` / `cierre_rechazado`, at `validado_en`, by the validator).

Semaforo per lab (calendar days in America/La_Paz):
- rojo: at least one lost object `en_custodia` that is not "vencido" (found at
  most 90 days ago). Django turned red on the lab's novedades whose effective
  estado was "pendiente", which excludes the vencidos;
- amarillo: a PC of the lab had an attention in the last 7 days (Django's rule:
  `fecha_registro >= today - 7` and a PC on the attention), or a PC is in
  mantenimiento or baja, or a baja request is still pendiente;
- verde: none of the above.
"""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.asignacion.sql import rows

# Same thresholds as Django (7 days of attentions) and G2 (90 days of custody).
DIAS_ATENCION = 7
DIAS_CUSTODIA = 90

_HOY = "(now() at time zone 'America/La_Paz')::date"


def _dia(columna: str) -> str:
    """La Paz calendar date of a timestamptz column."""
    return f"({columna} at time zone 'America/La_Paz')::date"


_TABLERO = text(
    f"""
    with pcs as (
      select ambiente_id,
             count(*) as total,
             count(*) filter (where estado = 'operativa') as operativas,
             count(*) filter (where estado = 'inactiva') as inactivas,
             count(*) filter (where estado = 'mantenimiento') as mantenimiento,
             count(*) filter (where estado = 'baja') as baja
        from horarios.ambiente_pcs
       group by ambiente_id
    ),
    recientes as (
      select a.ambiente_id,
             count(*) as atenciones,
             coalesce(array_agg(distinct p.etiqueta order by p.etiqueta)
                        filter (where p.id is not null), '{{}}') as pcs
        from horarios.atenciones a
        left join horarios.ambiente_pcs p on p.id = a.pc_id
       where {_dia("a.creado_en")} >= {_HOY} - {DIAS_ATENCION}
       group by a.ambiente_id
    ),
    objetos as (
      select ambiente_id,
             count(*) filter (where {_HOY} - {_dia("encontrado_en")} <= {DIAS_CUSTODIA})
               as en_custodia,
             count(*) filter (where {_HOY} - {_dia("encontrado_en")} > {DIAS_CUSTODIA})
               as vencidos
        from horarios.objetos_perdidos
       where estado = 'en_custodia'
       group by ambiente_id
    ),
    solicitudes as (
      select p.ambiente_id, count(*) as pendientes
        from horarios.solicitudes_baja s
        join horarios.ambiente_pcs p on p.id = s.pc_id
       where s.estado = 'pendiente'
       group by p.ambiente_id
    ),
    base as (
      select am.id as ambiente_id, am.codigo, am.nombre, am.color, am.estado, am.orden,
             coalesce(pcs.total, 0) as total_pcs,
             coalesce(pcs.operativas, 0) as pcs_operativas,
             coalesce(pcs.inactivas, 0) as pcs_inactivas,
             coalesce(pcs.mantenimiento, 0) as pcs_mantenimiento,
             coalesce(pcs.baja, 0) as pcs_baja,
             coalesce(r.atenciones, 0) as atenciones_7d,
             coalesce(r.pcs, '{{}}') as pcs_atendidas_7d,
             coalesce(o.en_custodia, 0) as objetos_en_custodia,
             coalesce(o.vencidos, 0) as objetos_vencidos,
             coalesce(s.pendientes, 0) as solicitudes_baja_pendientes,
             (select json_build_object(
                       'id', u.id, 'creado_en', u.creado_en, 'tipo', u.tipo,
                       'turno', u.turno, 'autor', pf.nombre_completo)
                from horarios.atenciones u
                left join horarios.perfiles pf on pf.id = u.auxiliar_id
               where u.ambiente_id = am.id
               order by u.creado_en desc, u.id desc
               limit 1) as ultima
        from horarios.ambientes am
        left join pcs on pcs.ambiente_id = am.id
        left join recientes r on r.ambiente_id = am.id
        left join objetos o on o.ambiente_id = am.id
        left join solicitudes s on s.ambiente_id = am.id
       where am.tipo = 'laboratorio' and am.estado <> 'baja'
    )
    select *,
           case
             when objetos_en_custodia > 0 then 'rojo'
             when cardinality(pcs_atendidas_7d) > 0 or pcs_mantenimiento > 0
                  or pcs_baja > 0 or solicitudes_baja_pendientes > 0 then 'amarillo'
             else 'verde'
           end as semaforo
      from base
     order by orden, codigo
    """
)


def tablero(db: Session) -> list[dict[str, Any]]:
    """One card per laboratory (not dado de baja) with its semaforo."""
    filas = [dict(r) for r in rows(db, _TABLERO)]
    for fila in filas:
        fila.pop("orden", None)
    return filas


# One branch per event kind; `foto` names the photo endpoint to use:
# 'objeto'|'entrega' -> /objetos-perdidos/{ref_id}/fotos/{foto},
# 'reporte' -> /reportes-turno/{ref_id}/foto. Photos already cleaned are null.
_TIMELINE = text(
    f"""
    with eventos as (
      select a.creado_en as momento, 'atencion' as evento, a.id as ref_id,
             a.ambiente_id, a.tipo as titulo, a.descripcion as detalle,
             a.auxiliar_id as autor_id, null::text as foto, pc.etiqueta as pc
        from horarios.atenciones a
        left join horarios.ambiente_pcs pc on pc.id = a.pc_id
       where {_dia("a.creado_en")} = :fecha
      union all
      select r.creado_en, 'reporte', r.id, null, r.turno, r.novedades,
             r.auxiliar_id, case when r.foto_path is not null then 'reporte' end, null
        from horarios.reportes_turno r
       where {_dia("r.creado_en")} = :fecha
      union all
      select t.hecha_en, 'tarea_hecha', t.id, t.ambiente_id, null, t.descripcion,
             t.hecha_por, null, null
        from horarios.reporte_tareas t
       where t.hecha and {_dia("t.hecha_en")} = :fecha
      union all
      select o.encontrado_en, 'objeto_registrado', o.id, o.ambiente_id, o.nombre,
             o.descripcion, o.encontrado_por,
             case when o.foto_path is not null then 'objeto' end, null
        from horarios.objetos_perdidos o
       where {_dia("o.encontrado_en")} = :fecha
      union all
      select o.entregado_en, 'objeto_entregado', o.id, o.ambiente_id, o.nombre,
             o.entregado_a, o.entregado_por,
             case when o.foto_entrega_path is not null then 'entrega' end, null
        from horarios.objetos_perdidos o
       where o.estado = 'entregado' and {_dia("o.entregado_en")} = :fecha
      union all
      select n.creado_en, 'novedad', n.id, n.ambiente_id, n.turno, n.texto,
             n.autor_id, case when n.foto_path is not null then 'novedad' end, null
        from horarios.novedades n
       where {_dia("n.creado_en")} = :fecha
      union all
      select r.validado_en, 'cierre_' || r.estado, r.id, null, r.turno, r.novedades,
             r.validado_por, null, null
        from horarios.reportes_turno r
       where r.estado <> 'pendiente' and {_dia("r.validado_en")} = :fecha
    )
    select e.evento, e.ref_id, e.momento,
           to_char(e.momento at time zone 'America/La_Paz', 'HH24:MI') as hora,
           e.titulo, e.detalle, e.pc, e.foto, e.ambiente_id,
           am.codigo as ambiente_codigo, am.color as ambiente_color,
           pf.nombre_completo as autor
      from eventos e
      left join horarios.ambientes am on am.id = e.ambiente_id
      left join horarios.perfiles pf on pf.id = e.autor_id
     order by e.momento desc, e.evento, e.ref_id desc
     limit :limite
    """
)

_HOY_SQL = text(f"select {_HOY}")

# Guard against a pathological day; a normal day has a few dozen events.
LIMITE_EVENTOS = 1000


def timeline(db: Session, fecha: date | None) -> dict[str, Any]:
    """Events of one La Paz day (today by default), newest first like Django."""
    dia = fecha or db.execute(_HOY_SQL).scalar_one()
    eventos = rows(db, _TIMELINE, {"fecha": dia, "limite": LIMITE_EVENTOS})
    return {"fecha": dia, "eventos": [dict(e) for e in eventos]}
