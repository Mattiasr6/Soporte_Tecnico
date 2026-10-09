import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { EstadoSoftwarePc, SoftwarePc } from '../../core/modelos';

/** A state change asked by the user */
export interface MarcaSoftwarePc {
  softwareId: number;
  estado: EstadoSoftwarePc;
}

const OPCIONES: { valor: EstadoSoftwarePc; texto: string; activo: string }[] = [
  { valor: 'instalado', texto: 'OK', activo: 'border-emerald-600 bg-emerald-50 text-emerald-700 font-bold' },
  { valor: 'falta', texto: 'Falta', activo: 'border-amber-600 bg-amber-50 text-amber-800 font-bold' },
  { valor: 'dañado', texto: 'Dañado', activo: 'border-rose-700 bg-rose-50 text-rose-700 font-bold' },
];

/**
 * Software states of one PC (presentational), like the Django "Estados" panel
 * of the lab room: one row per software of the lab with OK / Falta / Dañado.
 * `puedeMarcar` enables the buttons (the container applies role and PC state).
 */
@Component({
  selector: 'app-software-pc',
  imports: [DatePipe],
  template: `
    @if (cargando()) {
      <p class="py-6 text-center text-sm text-slate-500">Cargando…</p>
    } @else {
      @if (aviso()) { <p class="mb-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{{ aviso() }}</p> }
      <div class="divide-y divide-slate-100">
        @for (e of estados(); track e.software_id) {
          <div class="flex flex-wrap items-center gap-2 py-2">
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium">{{ e.nombre }}</p>
              @if (e.actualizado_en) {
                <p class="text-[11px] text-slate-400">{{ e.actualizado_por ?? '—' }} · {{ e.actualizado_en | date: 'dd/MM HH:mm' }}</p>
              } @else {
                <p class="text-[11px] text-slate-400">Sin verificar</p>
              }
            </div>
            <div class="flex gap-1" role="group" [attr.aria-label]="'Estado de ' + e.nombre">
              @for (o of opciones; track o.valor) {
                <button type="button" class="rounded-md border px-2 py-0.5 text-xs transition"
                        [class]="e.estado === o.valor ? o.activo : 'border-slate-200 text-slate-600 hover:bg-slate-50'"
                        [attr.aria-pressed]="e.estado === o.valor"
                        [disabled]="!puedeMarcar() || marcando() !== null || e.estado === o.valor"
                        (click)="marcar.emit({ softwareId: e.software_id, estado: o.valor })">{{ o.texto }}</button>
              }
            </div>
          </div>
        } @empty {
          <p class="py-6 text-center text-sm text-slate-500">Este laboratorio no tiene software asignado.</p>
        }
      </div>
    }
  `,
})
export class SoftwarePcComponent {
  readonly estados = input.required<SoftwarePc[]>();
  readonly puedeMarcar = input(false);
  readonly cargando = input(false);
  /** Software id being saved (buttons disabled meanwhile) */
  readonly marcando = input<number | null>(null);
  /** Why the buttons are disabled, if they are */
  readonly aviso = input<string | null>(null);
  readonly marcar = output<MarcaSoftwarePc>();

  protected readonly opciones = OPCIONES;
}
