import { Component, computed, input, signal } from '@angular/core';
import { numero } from './graficos';

/** Categorical slots in fixed order (defined by the page host, like desempeño) */
const COLORES = ['var(--serie-1)', 'var(--serie-2)', 'var(--serie-3)', 'var(--serie-4)', 'var(--serie-5)', 'var(--serie-6)'];
const RADIO = 60;
const GROSOR = 20;

/**
 * Donut chart (SVG) for a composition: one slice per label, a 2px surface gap
 * between slices, the total in the middle and a legend with value and share.
 * More than 6 slices fold into "Otros" so colors are never cycled.
 */
@Component({
  selector: 'app-grafico-dona',
  template: `
    @if (porciones().length) {
      <div class="flex flex-wrap items-center gap-4">
        <div class="relative shrink-0" (mouseleave)="indice.set(null)">
          <svg [attr.width]="lado" [attr.height]="lado" [attr.viewBox]="'0 0 ' + lado + ' ' + lado" role="img" [attr.aria-label]="descripcion()">
            @for (p of porciones(); track p.etiqueta; let i = $index) {
              <path [attr.d]="p.d" [style.fill]="p.color" style="stroke: var(--color-superficie)" stroke-width="2"
                    [attr.opacity]="indice() === null || indice() === i ? 1 : 0.45"
                    (mouseenter)="indice.set(i)" (pointerdown)="indice.set(i)" />
            }
            <text [attr.x]="lado / 2" [attr.y]="lado / 2 - 2" text-anchor="middle" class="fill-slate-800 text-lg font-bold tabular-nums">{{ centro().valor }}</text>
            <text [attr.x]="lado / 2" [attr.y]="lado / 2 + 14" text-anchor="middle" class="fill-slate-500 text-[10px]">{{ centro().texto }}</text>
          </svg>
        </div>
        <ul class="min-w-36 flex-1 space-y-1 text-xs text-slate-600">
          @for (p of porciones(); track p.etiqueta; let i = $index) {
            <li class="flex items-center gap-1.5" [class.font-semibold]="indice() === i" (mouseenter)="indice.set(i)" (mouseleave)="indice.set(null)">
              <span class="h-2.5 w-2.5 shrink-0 rounded-full" [style.background]="p.color"></span>
              <span class="truncate">{{ p.etiqueta }}</span>
              <b class="ml-auto pl-2 text-slate-800 tabular-nums">{{ p.valor }}</b>
              <span class="w-12 text-right tabular-nums">{{ formato(p.pct) }}%</span>
            </li>
          }
        </ul>
      </div>
    } @else {
      <p class="py-6 text-center text-sm text-slate-500">{{ vacio() }}</p>
    }
  `,
})
export class GraficoDonaComponent {
  readonly etiquetas = input.required<string[]>();
  readonly valores = input.required<number[]>();
  readonly vacio = input('Sin datos.');

  protected readonly lado = 2 * RADIO + 4;
  protected readonly indice = signal<number | null>(null);
  private readonly total = computed(() => this.valores().reduce((t, v) => t + v, 0));

  /** Slices with their arc path; past 6 the rest is folded into "Otros" */
  protected readonly porciones = computed(() => {
    const total = this.total();
    if (!total) return [];
    let filas = this.etiquetas().map((e, i) => ({ etiqueta: e, valor: this.valores()[i] ?? 0 })).filter((f) => f.valor > 0);
    if (filas.length > COLORES.length) {
      const resto = filas.slice(COLORES.length - 1).reduce((t, f) => t + f.valor, 0);
      filas = [...filas.slice(0, COLORES.length - 1), { etiqueta: 'Otros', valor: resto }];
    }
    let inicio = -Math.PI / 2;
    return filas.map((f, i) => {
      const angulo = (f.valor / total) * Math.PI * 2;
      const d = arco(this.lado / 2, inicio, inicio + angulo);
      inicio += angulo;
      return { ...f, color: COLORES[i], pct: (f.valor * 100) / total, d };
    });
  });

  protected readonly centro = computed(() => {
    const i = this.indice();
    const p = i === null ? null : this.porciones()[i];
    return p ? { valor: `${this.formato(p.pct)}%`, texto: p.etiqueta } : { valor: String(this.total()), texto: 'total' };
  });

  protected readonly descripcion = computed(() =>
    `Gráfico de dona: ${this.porciones().map((p) => `${p.etiqueta} ${p.valor}`).join(', ')}`);

  protected formato(v: number): string {
    return numero(Math.round(v * 10) / 10);
  }
}

/** Ring segment between two angles (a full circle is drawn as two halves) */
function arco(c: number, desde: number, hasta: number): string {
  if (hasta - desde >= Math.PI * 2 - 1e-6) {
    return arco(c, desde, desde + Math.PI) + ' ' + arco(c, desde + Math.PI, hasta);
  }
  const r1 = RADIO;
  const r2 = RADIO - GROSOR;
  const p = (r: number, a: number) => `${(c + r * Math.cos(a)).toFixed(2)},${(c + r * Math.sin(a)).toFixed(2)}`;
  const grande = hasta - desde > Math.PI ? 1 : 0;
  return `M${p(r1, desde)} A${r1},${r1} 0 ${grande} 1 ${p(r1, hasta)} L${p(r2, hasta)} A${r2},${r2} 0 ${grande} 0 ${p(r2, desde)} Z`;
}
