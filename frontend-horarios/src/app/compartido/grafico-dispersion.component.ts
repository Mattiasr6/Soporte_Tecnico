import { AfterViewInit, Component, computed, ElementRef, input, OnDestroy, signal, viewChild } from '@angular/core';
import { numero, topeRedondo } from './graficos';

/** One dot: x, y, its name and an optional note for the tooltip */
export interface PuntoDispersion {
  x: number;
  y: number;
  nombre: string;
  nota?: string;
}

const MARGEN = { arriba: 14, derecha: 16, abajo: 34, izquierda: 46 };

/**
 * Scatter chart (SVG): one dot per item with a 2px surface ring, the first
 * word of its name above it, dashed guides at half of the highest values
 * (as the Django dashboard) and a tooltip on hover.
 */
@Component({
  selector: 'app-grafico-dispersion',
  template: `
    <div #caja class="relative w-full" [style.height.px]="alto()" (mouseleave)="indice.set(null)">
      @if (ancho() > 0) {
        <svg [attr.width]="ancho()" [attr.height]="alto()" class="block" role="img" [attr.aria-label]="'Dispersión: ' + ejeX() + ' contra ' + ejeY()">
          @for (g of rejillaY(); track g.v) {
            <line [attr.x1]="m.izquierda" [attr.x2]="ancho() - m.derecha" [attr.y1]="g.p" [attr.y2]="g.p" class="stroke-slate-200" />
            <text [attr.x]="m.izquierda - 6" [attr.y]="g.p + 3" text-anchor="end" class="fill-slate-400 text-[10px] tabular-nums">{{ g.t }}</text>
          }
          @for (g of rejillaX(); track g.v) {
            <text [attr.x]="g.p" [attr.y]="alto() - m.abajo + 14" text-anchor="middle" class="fill-slate-400 text-[10px] tabular-nums">{{ g.t }}</text>
          }
          <line [attr.x1]="x(guia().x)" [attr.x2]="x(guia().x)" [attr.y1]="m.arriba" [attr.y2]="alto() - m.abajo" class="stroke-slate-400" stroke-dasharray="4 4" />
          <line [attr.x1]="m.izquierda" [attr.x2]="ancho() - m.derecha" [attr.y1]="y(guia().y)" [attr.y2]="y(guia().y)" class="stroke-slate-400" stroke-dasharray="4 4" />
          <text [attr.x]="m.izquierda + utilX() / 2" [attr.y]="alto() - 4" text-anchor="middle" class="fill-slate-500 text-[10px]">{{ ejeX() }}</text>
          <text [attr.transform]="'translate(12,' + (m.arriba + utilY() / 2) + ') rotate(-90)'" text-anchor="middle" class="fill-slate-500 text-[10px]">{{ ejeY() }}</text>
          @for (p of puntos(); track $index; let i = $index) {
            <circle [attr.cx]="x(p.x)" [attr.cy]="y(p.y)" r="7" stroke-width="2" style="fill: var(--serie-1); stroke: var(--color-superficie)"
                    [attr.opacity]="indice() === null || indice() === i ? 1 : 0.5" />
            @if (rotulados().has(i)) {
              <text [attr.x]="x(p.x)" [attr.y]="y(p.y) - 11" text-anchor="middle" class="fill-slate-600 text-[10px]">{{ p.nombre.split(' ')[0] }}</text>
            }
            <circle [attr.cx]="x(p.x)" [attr.cy]="y(p.y)" r="14" fill="transparent" (mouseenter)="indice.set(i)" (pointerdown)="indice.set(i)" />
          }
        </svg>
      }
      @if (indice() !== null) {
        @let p = puntos()[indice()!];
        <div class="pointer-events-none absolute z-10 min-w-40 rounded-lg border border-slate-200 bg-superficie px-3 py-2 text-xs shadow-lg"
             [style.left.px]="Math.min(x(p.x) + 10, ancho() - 180)" [style.top.px]="Math.max(0, y(p.y) - 50)">
          <p class="font-semibold text-slate-800">{{ p.nombre }}</p>
          <p class="text-slate-600">{{ p.x }} {{ ejeX() }} · {{ p.y }} {{ ejeY() }}@if (p.nota) { ({{ p.nota }}) }</p>
        </div>
      }
    </div>
  `,
})
export class GraficoDispersionComponent implements AfterViewInit, OnDestroy {
  readonly puntos = input.required<PuntoDispersion[]>();
  readonly ejeX = input('');
  readonly ejeY = input('');
  readonly alto = input(260);

  protected readonly Math = Math;
  protected readonly m = MARGEN;
  private readonly caja = viewChild.required<ElementRef<HTMLElement>>('caja');
  protected readonly ancho = signal(0);
  protected readonly indice = signal<number | null>(null);
  private observador?: ResizeObserver;

  protected readonly utilX = computed(() => Math.max(10, this.ancho() - MARGEN.izquierda - MARGEN.derecha));
  protected readonly utilY = computed(() => Math.max(10, this.alto() - MARGEN.arriba - MARGEN.abajo));
  protected readonly topeX = computed(() => topeRedondo(Math.max(0, ...this.puntos().map((p) => p.x))));
  protected readonly topeY = computed(() => topeRedondo(Math.max(0, ...this.puntos().map((p) => p.y))));
  /** Dashed guides at half of the highest x and y (Django markLine at max * 0.5) */
  protected readonly guia = computed(() => ({
    x: Math.max(1, ...this.puntos().map((p) => p.x)) / 2,
    y: Math.max(1, ...this.puntos().map((p) => p.y)) / 2,
  }));
  protected readonly rejillaY = computed(() => [0, this.topeY() / 2, this.topeY()].map((v) => ({ v, p: this.y(v), t: numero(v) })));
  protected readonly rejillaX = computed(() => [0, this.topeX() / 2, this.topeX()].map((v) => ({ v, p: this.x(v), t: numero(v) })));

  /**
   * Dots whose name is drawn: biggest x first, a label is skipped when it would
   * overlap one already placed (the tooltip still names every dot).
   */
  protected readonly rotulados = computed(() => {
    const puestos: { x: number; y: number; w: number }[] = [];
    const elegidos = new Set<number>();
    const orden = this.puntos().map((p, i) => ({ p, i })).sort((a, b) => b.p.x - a.p.x);
    for (const { p, i } of orden) {
      const r = { x: this.x(p.x), y: this.y(p.y), w: p.nombre.split(' ')[0].length * 6 + 6 };
      if (puestos.every((o) => Math.abs(o.x - r.x) > (o.w + r.w) / 2 || Math.abs(o.y - r.y) > 12)) {
        puestos.push(r);
        elegidos.add(i);
      }
    }
    return elegidos;
  });

  ngAfterViewInit(): void {
    const el = this.caja().nativeElement;
    this.observador = new ResizeObserver(() => this.ancho.set(el.clientWidth));
    this.observador.observe(el);
    this.ancho.set(el.clientWidth);
  }

  ngOnDestroy(): void {
    this.observador?.disconnect();
  }

  protected x(v: number): number {
    return MARGEN.izquierda + (v / this.topeX()) * this.utilX();
  }

  protected y(v: number): number {
    return MARGEN.arriba + this.utilY() - (v / this.topeY()) * this.utilY();
  }
}
