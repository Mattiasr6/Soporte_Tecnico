import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { hhmm } from '../../core/fechas';
import { EstadoCierre, ReporteTurno, TurnoCodigo } from '../../core/modelos';
import { textoRetraso } from '../../core/operacion.service';
import { TURNOS_TICKET } from '../../core/tickets';

const NOMBRE_TURNO = Object.fromEntries(TURNOS_TICKET.map((t) => [t.valor, t.texto])) as Record<TurnoCodigo, string>;

const ESTADOS: Record<EstadoCierre, { texto: string; clase: string }> = {
  pendiente: { texto: 'Pendiente', clase: 'bg-amber-100 text-amber-800' },
  validado: { texto: 'Validado', clase: 'bg-emerald-100 text-emerald-700' },
  rechazado: { texto: 'Rechazado', clase: 'bg-red-100 text-red-700' },
};

/** A decision taken on one close */
export interface DecisionCierre {
  reporte: ReporteTurno;
  estado: Exclude<EstadoCierre, 'pendiente'>;
}

/**
 * Shift closes to validate (presentational), like Django's "cierres" tab: the
 * report with its turno, delay, author, novedades, PCs given de baja, task
 * count and key photo. Pending ones get Validar/Rechazar unless `esPropio`
 * says the viewer wrote it (the API refuses it too); decided ones show who
 * decided and when.
 */
@Component({
  selector: 'app-cierres-lista',
  imports: [DatePipe, IconoComponent],
  template: `
    <div class="space-y-2">
      @for (r of cierres(); track r.id) {
        <article class="tarjeta flex gap-3 p-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="chip" [class]="estados[r.estado ?? 'pendiente'].clase">{{ estados[r.estado ?? 'pendiente'].texto }}</span>
              <span class="chip bg-marca-50 text-marca-700">
                Turno {{ nombreTurno[r.turno].toLowerCase() }}@if (r.hora_inicio_turno && r.hora_fin_turno) { · {{ hhmm(r.hora_inicio_turno) }}–{{ hhmm(r.hora_fin_turno) }} }
              </span>
              @if (r.minutos_retraso) {
                <span class="chip bg-amber-100 text-amber-800">{{ textoRetraso(r.minutos_retraso) }} de retraso</span>
              }
              <span class="text-sm font-semibold">{{ r.creado_en | date: 'EEE dd/MM/yyyy HH:mm' }}</span>
              <span class="text-sm text-slate-500">· {{ r.autor?.nombre_completo || '—' }}</span>
            </div>
            @if (r.novedades) { <p class="mt-1.5 text-sm break-words whitespace-pre-line text-slate-700">{{ r.novedades }}</p> }
            <p class="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-500">
              <span>{{ r.tareas?.length ?? 0 }} tarea(s) pendiente(s) dejadas</span>
              @if (r.pcs_baja?.length) {
                <span class="text-red-700">PCs dadas de baja: {{ etiquetasBaja(r) }}</span>
              }
              @if (!r.foto_path) { <span>Sin foto de llaves (o ya expiró)</span> }
            </p>
            @if (r.estado && r.estado !== 'pendiente') {
              <p class="mt-1 text-xs text-slate-500">
                {{ estados[r.estado].texto }} por {{ r.validador?.nombre_completo || '—' }} · {{ r.validado_en | date: 'dd/MM HH:mm' }}
              </p>
            } @else if (esPropio()(r)) {
              <p class="mt-1 text-xs text-slate-500">Es tu cierre: lo valida otro encargado o el jefe.</p>
            } @else {
              <div class="mt-2 flex gap-2">
                <button class="btn-primario btn-sm" [disabled]="ocupado() === r.id" (click)="decidir.emit({ reporte: r, estado: 'validado' })">
                  <app-icono nombre="check" [tamano]="14" /> Validar
                </button>
                <button class="btn-secundario btn-sm text-red-700" [disabled]="ocupado() === r.id" (click)="decidir.emit({ reporte: r, estado: 'rechazado' })">
                  <app-icono nombre="cerrar" [tamano]="14" /> Rechazar
                </button>
              </div>
            }
          </div>
          @if (r.foto_path) {
            @if (fotos().get(r.id); as url) {
              <button type="button" class="h-20 w-20 shrink-0 overflow-hidden rounded-md bg-slate-100" (click)="verFoto.emit({ url, titulo: 'Llaves · ' + (r.autor?.nombre_completo || '') })" aria-label="Ver foto">
                <img [src]="url" alt="Foto del cierre" class="h-full w-full object-cover" loading="lazy">
              </button>
            } @else {
              <span class="flex h-20 w-20 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-400"><app-icono nombre="camara" [tamano]="22" /></span>
            }
          }
        </article>
      } @empty {
        <p class="tarjeta py-10 text-center text-sm text-slate-500">{{ vacio() }}</p>
      }
    </div>
  `,
})
export class CierresListaComponent {
  readonly cierres = input.required<ReporteTurno[]>();
  readonly fotos = input.required<Map<number, string>>();
  readonly esPropio = input.required<(r: ReporteTurno) => boolean>();
  /** Id of the close whose decision is being saved */
  readonly ocupado = input<number | null>(null);
  readonly vacio = input('No hay cierres en este estado.');
  readonly decidir = output<DecisionCierre>();
  readonly verFoto = output<{ url: string; titulo: string }>();

  protected readonly estados = ESTADOS;
  protected readonly nombreTurno = NOMBRE_TURNO;
  protected readonly hhmm = hhmm;
  protected readonly textoRetraso = textoRetraso;

  protected etiquetasBaja(r: ReporteTurno): string {
    return (r.pcs_baja ?? []).map((p) => p.etiqueta).join(', ');
  }
}
