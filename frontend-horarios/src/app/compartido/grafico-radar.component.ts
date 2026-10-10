import { Component, computed, input } from '@angular/core';

/** Wide view box: room for the axis names on both sides */
const LADO = 380;
const RADIO = 86;

/**
 * Radar chart (SVG) of one profile: one axis per label, all on the same
 * scale `max`, a filled polygon in --serie-1 and each value in its vertex
 * title. Used for "Perfil por técnico" (cases per category).
 */
@Component({
  selector: 'app-grafico-radar',
  template: `
    @if (ejes().length >= 3) {
      <svg class="mx-auto block w-full max-w-md" [attr.viewBox]="'0 0 ' + lado + ' ' + lado" role="img" [attr.aria-label]="descripcion()">
        @for (n of [0.25, 0.5, 0.75, 1]; track n) {
          <polygon [attr.points]="anillo(n)" fill="none" class="stroke-slate-200" />
        }
        @for (e of puntas(); track $index) {
          <line [attr.x1]="c" [attr.y1]="c" [attr.x2]="e.x" [attr.y2]="e.y" class="stroke-slate-200" />
          <text [attr.x]="e.tx" [attr.y]="e.ty" [attr.text-anchor]="e.ancla" class="fill-slate-600 text-[9px]">{{ e.nombre }}</text>
        }
        <polygon [attr.points]="forma()" style="fill: color-mix(in oklab, var(--serie-1) 22%, transparent); stroke: var(--serie-1)" stroke-width="2" stroke-linejoin="round" />
        @for (p of vertices(); track $index) {
          <circle [attr.cx]="p.x" [attr.cy]="p.y" r="4" stroke-width="2" style="fill: var(--serie-1); stroke: var(--color-superficie)">
            <title>{{ p.nombre }}: {{ p.v }}</title>
          </circle>
        }
      </svg>
    } @else {
      <ul class="space-y-1 text-sm">
        @for (e of ejes(); track $index) { <li class="flex justify-between"><span>{{ e }}</span><b class="tabular-nums">{{ valores()[$index] ?? 0 }}</b></li> }
      </ul>
    }
  `,
})
export class GraficoRadarComponent {
  readonly ejes = input.required<string[]>();
  readonly valores = input.required<number[]>();
  /** Shared scale so profiles can be compared (Django: the highest value of any technician) */
  readonly max = input(1);

  protected readonly lado = LADO;
  protected readonly c = LADO / 2;

  private punto(i: number, r: number): { x: number; y: number } {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / this.ejes().length;
    return { x: this.c + r * Math.cos(a), y: this.c + r * Math.sin(a) };
  }

  protected anillo(n: number): string {
    return this.ejes().map((_, i) => this.punto(i, RADIO * n)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  }

  protected readonly puntas = computed(() =>
    this.ejes().map((nombre, i) => {
      const p = this.punto(i, RADIO);
      const t = this.punto(i, RADIO + 14);
      const ancla = Math.abs(t.x - this.c) < 8 ? 'middle' : t.x > this.c ? 'start' : 'end';
      return { ...p, tx: t.x, ty: t.y + 3, ancla, nombre: nombre.length > 18 ? nombre.slice(0, 17) + '…' : nombre };
    }));

  protected readonly vertices = computed(() => {
    const max = Math.max(1, this.max());
    return this.ejes().map((nombre, i) => {
      const v = this.valores()[i] ?? 0;
      return { ...this.punto(i, (RADIO * v) / max), v, nombre };
    });
  });

  protected readonly forma = computed(() => this.vertices().map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '));
  protected readonly descripcion = computed(() =>
    `Radar: ${this.ejes().map((e, i) => `${e} ${this.valores()[i] ?? 0}`).join(', ')}`);
}
