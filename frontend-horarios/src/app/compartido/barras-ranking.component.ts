import { NgTemplateOutlet } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';
import { numero } from './graficos';

/** One row of a ranking: label, value and an optional id the click reports */
export interface FilaRanking {
  etiqueta: string;
  valor: number;
  id?: string | number;
  /** Optional text after the value (e.g. '60%') */
  extra?: string;
}

/**
 * Horizontal ranked bars (HTML + CSS widths), for long category or area names
 * that do not fit under vertical bars. Same look as the "Medio de solicitud"
 * list of Labs por turno. With `seleccionable` every row is a button and
 * `elegir` reports it (drill-down filters).
 */
@Component({
  selector: 'app-barras-ranking',
  template: `
    @if (filas().length) {
      <ul class="space-y-2 text-sm">
        @for (f of filas(); track $index) {
          <li>
            @if (seleccionable()) {
              <button type="button" class="block w-full rounded-md px-1 py-0.5 text-left hover:bg-slate-100" (click)="elegir.emit(f)"
                      [title]="'Filtrar por ' + f.etiqueta">
                <ng-container *ngTemplateOutlet="fila; context: { $implicit: f }" />
              </button>
            } @else {
              <div class="px-1 py-0.5" [title]="f.etiqueta + ': ' + f.valor"><ng-container *ngTemplateOutlet="fila; context: { $implicit: f }" /></div>
            }
          </li>
        }
      </ul>
      <ng-template #fila let-f>
        <div class="flex items-baseline justify-between gap-3">
          <span class="min-w-0 truncate">{{ f.etiqueta }}</span>
          <span class="shrink-0 text-slate-800"><b class="tabular-nums">{{ formato(f.valor) }}</b>
            @if (f.extra) { <span class="ml-1 text-xs text-slate-500 tabular-nums">{{ f.extra }}</span> }</span>
        </div>
        <div class="mt-1 h-2 rounded bg-slate-100">
          <div class="h-2 rounded-r" [style.width.%]="tope() ? (f.valor * 100) / tope() : 0" [style.background]="color()"></div>
        </div>
      </ng-template>
    } @else {
      <p class="py-6 text-center text-sm text-slate-500">{{ vacio() }}</p>
    }
  `,
  imports: [NgTemplateOutlet],
})
export class BarrasRankingComponent {
  readonly filas = input.required<FilaRanking[]>();
  readonly color = input('var(--serie-1)');
  readonly seleccionable = input(false);
  readonly vacio = input('Sin datos.');
  readonly elegir = output<FilaRanking>();

  protected readonly tope = computed(() => Math.max(0, ...this.filas().map((f) => f.valor)));

  protected formato(v: number): string {
    return numero(v);
  }
}
