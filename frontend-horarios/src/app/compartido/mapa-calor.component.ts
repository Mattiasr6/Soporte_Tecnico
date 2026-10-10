import { Component, computed, input } from '@angular/core';

/** Cell value; null marks an empty slot (e.g. a calendar day outside the range) */
export type CeldaCalor = number | null;

/**
 * Heatmap (HTML grid): rows × columns, one sequential hue (--serie-1) from
 * light (few) to dark (many). With `numeros` each cell shows its value;
 * otherwise the value is in the cell title. A min-max legend sits below.
 */
@Component({
  selector: 'app-mapa-calor',
  template: `
    <div class="overflow-x-auto">
      <table class="border-separate text-[10px]" [style.border-spacing.px]="2" role="img" [attr.aria-label]="descripcion()">
        <thead>
          <tr>
            <th></th>
            @for (c of columnas(); track $index) {
              <th class="px-0.5 font-normal whitespace-nowrap text-slate-400">{{ c }}</th>
            }
          </tr>
        </thead>
        <tbody>
          @for (f of filas(); track $index; let i = $index) {
            <tr>
              <th class="pr-2 text-right font-normal whitespace-nowrap text-slate-600">{{ f }}</th>
              @for (v of valores()[i]; track $index; let j = $index) {
                @if (v === null) {
                  <td [style.width.px]="tamano()" [style.height.px]="tamano()"></td>
                } @else {
                  <td class="rounded-sm text-center tabular-nums" [style.width.px]="numeros() ? null : tamano()" [style.height.px]="tamano()"
                      [style.min-width.px]="tamano()" [style.background]="fondo(v)" [style.color]="tinta(v)"
                      [title]="(titulos()?.[i]?.[j] ?? f + ' · ' + columnas()[j]) + ': ' + v">
                    @if (numeros()) { {{ v }} }
                  </td>
                }
              }
            </tr>
          }
        </tbody>
      </table>
    </div>
    <div class="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
      <span>0</span>
      <span class="h-2 w-28 rounded" style="background: linear-gradient(to right, var(--color-slate-100), var(--serie-1))"></span>
      <span>{{ max() }}</span>
    </div>
  `,
})
export class MapaCalorComponent {
  readonly filas = input.required<string[]>();
  readonly columnas = input.required<string[]>();
  /** valores[fila][columna] */
  readonly valores = input.required<CeldaCalor[][]>();
  /** Optional cell titles (same shape as valores) */
  readonly titulos = input<string[][]>();
  readonly numeros = input(false);
  readonly tamano = input(14);

  protected readonly max = computed(() => Math.max(1, ...this.valores().flat().map((v) => v ?? 0)));
  protected readonly descripcion = computed(() => `Mapa de calor de ${this.filas().length} filas por ${this.columnas().length} columnas`);

  /** Share of the hue: 0 is the empty step, then 18%–100% so low values stay visible */
  private parte(v: number): number {
    return v <= 0 ? 0 : 18 + (82 * v) / this.max();
  }

  protected fondo(v: number): string {
    const p = this.parte(v);
    return p ? `color-mix(in oklab, var(--serie-1) ${p.toFixed(0)}%, var(--color-superficie))` : 'var(--color-slate-100)';
  }

  protected tinta(v: number): string {
    return this.parte(v) > 55 ? '#fff' : 'var(--color-slate-700)';
  }
}
