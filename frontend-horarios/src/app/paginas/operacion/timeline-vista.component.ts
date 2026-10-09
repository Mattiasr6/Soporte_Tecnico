import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { TipoAtencion, TurnoCodigo } from '../../core/modelos';
import { TIPOS_TICKET, TURNOS_TICKET } from '../../core/tickets';

export type TipoEvento =
  | 'atencion' | 'reporte' | 'tarea_hecha' | 'objeto_registrado' | 'objeto_entregado'
  | 'novedad' | 'cierre_validado' | 'cierre_rechazado';

/** One event of GET /timeline (newest first) */
export interface EventoTimeline {
  evento: TipoEvento;
  ref_id: number;
  momento: string;
  /** HH:MM in La Paz, computed by the API */
  hora: string;
  /** atencion: tipo; reporte, novedad and cierre: turno; objetos: object name */
  titulo: string | null;
  /** atencion: descripción; reporte/cierre: novedades; novedad: texto; tarea: descripción; entrega: who received it */
  detalle: string | null;
  pc: string | null;
  /** Which photo endpoint applies (see rutaFoto), null when there is none */
  foto: 'objeto' | 'entrega' | 'reporte' | 'novedad' | null;
  ambiente_id: number | null;
  ambiente_codigo: string | null;
  ambiente_color: string | null;
  autor: string | null;
}

/** API path of the event's photo, served by the existing photo endpoints */
export function rutaFoto(e: EventoTimeline): string | null {
  if (e.foto === 'reporte') return `/reportes-turno/${e.ref_id}/foto`;
  if (e.foto === 'novedad') return `/novedades/${e.ref_id}/foto`;
  if (e.foto) return `/objetos-perdidos/${e.ref_id}/fotos/${e.foto}`;
  return null;
}

const ICONOS: Record<TipoEvento, { icono: string; clase: string }> = {
  atencion: { icono: 'mantenimiento', clase: 'bg-marca-50 text-marca-700' },
  reporte: { icono: 'registros', clase: 'bg-slate-100 text-slate-700' },
  tarea_hecha: { icono: 'ok', clase: 'bg-emerald-50 text-emerald-700' },
  objeto_registrado: { icono: 'objeto', clase: 'bg-amber-50 text-amber-800' },
  objeto_entregado: { icono: 'entregar', clase: 'bg-emerald-50 text-emerald-700' },
  novedad: { icono: 'novedad', clase: 'bg-sky-50 text-sky-700' },
  cierre_validado: { icono: 'cierre', clase: 'bg-emerald-50 text-emerald-700' },
  cierre_rechazado: { icono: 'cierre', clase: 'bg-red-50 text-red-700' },
};

const NOMBRE_TURNO = Object.fromEntries(TURNOS_TICKET.map((t) => [t.valor, t.texto])) as Record<TurnoCodigo, string>;

/**
 * Day timeline (presentational), like Django `timeline.html`: one row per
 * event with its time, icon, lab, author and photo thumbnail. `fotos` maps a
 * photo path (rutaFoto) to a local blob URL; clicking a thumbnail is emitted.
 */
@Component({
  selector: 'app-timeline-vista',
  imports: [IconoComponent],
  template: `
    <ol class="space-y-2">
      @for (e of eventos(); track e.evento + e.ref_id) {
        <li class="tarjeta flex gap-3 p-3">
          <div class="flex w-14 shrink-0 flex-col items-center gap-1">
            <span class="text-sm font-semibold tabular-nums text-slate-700">{{ e.hora }}</span>
            <span class="flex h-8 w-8 items-center justify-center rounded-full" [class]="iconos[e.evento].clase">
              <app-icono [nombre]="iconos[e.evento].icono" [tamano]="16" />
            </span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-x-2 font-medium text-slate-800">
              {{ titulo(e) }}
              @if (e.ambiente_codigo) {
                <span class="inline-flex items-center gap-1 text-xs font-semibold text-slate-600">
                  <span class="h-2 w-2 rounded-full" [style.background]="e.ambiente_color"></span>{{ e.ambiente_codigo }}
                </span>
              }
            </p>
            @if (detalle(e); as d) { <p class="mt-0.5 text-sm break-words whitespace-pre-line text-slate-600">{{ d }}</p> }
            <p class="mt-0.5 text-xs text-slate-500">{{ e.autor || 'Sin autor' }}</p>
          </div>
          @if (rutaFoto(e); as ruta) {
            @if (fotos().get(ruta); as url) {
              <button type="button" class="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-slate-100" (click)="verFoto.emit({ url, titulo: titulo(e) })" aria-label="Ver foto">
                <img [src]="url" alt="Foto del evento" class="h-full w-full object-cover" loading="lazy">
              </button>
            }
          }
        </li>
      } @empty {
        <li class="tarjeta p-8 text-center text-sm text-slate-500">No hay actividad registrada este día.</li>
      }
    </ol>
  `,
})
export class TimelineVistaComponent {
  readonly eventos = input.required<EventoTimeline[]>();
  readonly fotos = input.required<Map<string, string>>();
  readonly verFoto = output<{ url: string; titulo: string }>();

  protected readonly iconos = ICONOS;
  protected readonly rutaFoto = rutaFoto;

  protected titulo(e: EventoTimeline): string {
    switch (e.evento) {
      case 'atencion': {
        const tipo = TIPOS_TICKET[e.titulo as TipoAtencion]?.texto ?? e.titulo ?? 'Atención';
        return e.pc ? `${tipo} · ${e.pc}` : tipo;
      }
      case 'reporte':
        return `Reporte de turno ${NOMBRE_TURNO[e.titulo as TurnoCodigo] ?? e.titulo ?? ''}`.trim();
      case 'tarea_hecha':
        return 'Tarea pendiente hecha';
      case 'objeto_registrado':
        return `Objeto registrado: ${e.titulo ?? ''}`;
      case 'objeto_entregado':
        return `Objeto entregado: ${e.titulo ?? ''}`;
      case 'novedad':
        return `Novedad · turno ${(NOMBRE_TURNO[e.titulo as TurnoCodigo] ?? e.titulo ?? '').toLowerCase()}`;
      case 'cierre_validado':
      case 'cierre_rechazado': {
        const turno = (NOMBRE_TURNO[e.titulo as TurnoCodigo] ?? e.titulo ?? '').toLowerCase();
        return `Cierre de turno ${turno} ${e.evento === 'cierre_validado' ? 'validado' : 'rechazado'}`;
      }
    }
  }

  protected detalle(e: EventoTimeline): string | null {
    if (e.evento === 'objeto_entregado') return e.detalle ? `Entregado a ${e.detalle}` : null;
    return e.detalle;
  }
}
