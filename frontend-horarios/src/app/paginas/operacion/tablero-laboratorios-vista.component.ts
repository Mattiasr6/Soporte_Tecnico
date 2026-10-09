import { DatePipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { TipoAtencion, TurnoCodigo } from '../../core/modelos';
import { TIPOS_TICKET } from '../../core/tickets';

export type Semaforo = 'rojo' | 'amarillo' | 'verde';

/** One card of GET /tablero-laboratorios */
export interface TarjetaLaboratorio {
  ambiente_id: number;
  codigo: string;
  nombre: string | null;
  color: string;
  estado: 'activo' | 'mantenimiento' | 'baja';
  total_pcs: number;
  pcs_operativas: number;
  pcs_inactivas: number;
  pcs_mantenimiento: number;
  pcs_baja: number;
  atenciones_7d: number;
  pcs_atendidas_7d: string[];
  objetos_en_custodia: number;
  objetos_vencidos: number;
  solicitudes_baja_pendientes: number;
  ultima: { id: number; creado_en: string; tipo: TipoAtencion; turno: TurnoCodigo; autor: string | null } | null;
  semaforo: Semaforo;
}

/** Look of each traffic-light state */
export const SEMAFOROS: Record<Semaforo, { texto: string; punto: string; borde: string; chip: string }> = {
  rojo: { texto: 'Rojo', punto: 'bg-red-500', borde: 'border-red-300', chip: 'bg-red-50 text-red-700' },
  amarillo: { texto: 'Amarillo', punto: 'bg-amber-400', borde: 'border-amber-300', chip: 'bg-amber-50 text-amber-800' },
  verde: { texto: 'Verde', punto: 'bg-emerald-500', borde: 'border-emerald-300', chip: 'bg-emerald-50 text-emerald-700' },
};

/**
 * Lab traffic-light board (presentational), like Django `tablero.html`: a
 * summary of red/yellow/green labs and one card per lab with the reasons for
 * its state, its PCs and the last attention. Card actions are emitted.
 */
@Component({
  selector: 'app-tablero-laboratorios-vista',
  imports: [DatePipe, IconoComponent],
  template: `
    <div class="mb-4 flex flex-wrap gap-2">
      @for (s of orden; track s) {
        <span class="chip !px-3 !py-1 !text-sm" [class]="semaforos[s].chip">
          <span class="h-2.5 w-2.5 rounded-full" [class]="semaforos[s].punto"></span>
          {{ resumen()[s] }} {{ semaforos[s].texto.toLowerCase() }}
        </span>
      }
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      @for (t of tarjetas(); track t.ambiente_id) {
        <article class="tarjeta flex flex-col border-l-4 p-4" [class]="semaforos[t.semaforo].borde">
          <header class="flex items-start justify-between gap-2">
            <div class="flex min-w-0 items-center gap-2">
              <span class="h-3 w-3 shrink-0 rounded-full" [class]="semaforos[t.semaforo].punto" [attr.aria-label]="'Semáforo ' + semaforos[t.semaforo].texto"></span>
              <div class="min-w-0">
                <p class="truncate font-semibold">{{ t.codigo }}</p>
                @if (t.nombre) { <p class="truncate text-xs text-slate-500">{{ t.nombre }}</p> }
              </div>
            </div>
            <span class="chip" [class]="semaforos[t.semaforo].chip">{{ semaforos[t.semaforo].texto }}</span>
          </header>

          <p class="mt-3 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-600">
            <span class="inline-flex items-center gap-1"><app-icono nombre="equipo" [tamano]="12" /> {{ t.pcs_operativas }}/{{ t.total_pcs }} PCs operativas</span>
            @if (t.estado === 'mantenimiento') { <span class="text-amber-700">Laboratorio en mantenimiento</span> }
          </p>

          <ul class="mt-2 space-y-0.5 text-xs">
            @if (t.objetos_en_custodia) {
              <li class="text-red-700">{{ t.objetos_en_custodia }} objeto(s) perdido(s) en custodia</li>
            }
            @if (t.pcs_atendidas_7d.length) {
              <li class="text-amber-800">PCs atendidas en 7 días: {{ t.pcs_atendidas_7d.join(', ') }}</li>
            }
            @if (t.pcs_mantenimiento) { <li class="text-amber-800">{{ t.pcs_mantenimiento }} PC(s) en mantenimiento</li> }
            @if (t.pcs_baja) { <li class="text-amber-800">{{ t.pcs_baja }} PC(s) de baja</li> }
            @if (t.solicitudes_baja_pendientes) {
              <li class="text-amber-800">{{ t.solicitudes_baja_pendientes }} solicitud(es) de baja pendiente(s)</li>
            }
            @if (t.objetos_vencidos) { <li class="text-slate-500">{{ t.objetos_vencidos }} objeto(s) vencido(s) +90 días</li> }
            <li class="text-slate-500">{{ t.atenciones_7d }} atención(es) en los últimos 7 días</li>
          </ul>

          <div class="mt-3 rounded-md bg-slate-50 px-2.5 py-2 text-xs">
            <p class="font-medium text-slate-600">Última atención</p>
            @if (t.ultima; as u) {
              <p class="mt-0.5 text-slate-700">{{ u.creado_en | date: 'dd/MM/yyyy HH:mm' }} · {{ nombreTipo(u.tipo) }}</p>
              <p class="text-slate-500">{{ u.autor || 'Sin autor' }}</p>
            } @else {
              <p class="mt-0.5 text-slate-500">Sin atenciones registradas.</p>
            }
          </div>

          <footer class="mt-3 flex flex-wrap gap-1.5">
            <button type="button" class="btn-secundario btn-sm" (click)="croquis.emit(t.ambiente_id)">
              <app-icono nombre="laboratorio" [tamano]="14" /> Croquis
            </button>
            <button type="button" class="btn-secundario btn-sm" (click)="atenciones.emit(t.ambiente_id)">
              <app-icono nombre="registros" [tamano]="14" /> Atenciones
            </button>
            <button type="button" class="btn-secundario btn-sm" (click)="objetos.emit(t.ambiente_id)">
              <app-icono nombre="objeto" [tamano]="14" /> Objetos
            </button>
          </footer>
        </article>
      } @empty {
        <p class="tarjeta col-span-full p-8 text-center text-sm text-slate-500">No hay laboratorios cargados.</p>
      }
    </div>
  `,
})
export class TableroLaboratoriosVistaComponent {
  readonly tarjetas = input.required<TarjetaLaboratorio[]>();
  readonly croquis = output<number>();
  readonly atenciones = output<number>();
  readonly objetos = output<number>();

  protected readonly semaforos = SEMAFOROS;
  protected readonly orden: Semaforo[] = ['rojo', 'amarillo', 'verde'];
  protected readonly resumen = computed(() => {
    const cuenta: Record<Semaforo, number> = { rojo: 0, amarillo: 0, verde: 0 };
    for (const t of this.tarjetas()) cuenta[t.semaforo]++;
    return cuenta;
  });

  protected nombreTipo(tipo: TipoAtencion): string {
    return TIPOS_TICKET[tipo]?.texto ?? tipo;
  }
}
