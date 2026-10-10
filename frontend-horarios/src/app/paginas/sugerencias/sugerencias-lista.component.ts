import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { Sugerencia } from '../../core/sugerencias.service';

/** Chip color and label per suggestion state */
const ESTADOS: Record<string, { texto: string; clase: string }> = {
  pendiente: { texto: 'Pendiente', clase: 'bg-amber-500 text-white' },
  revisada: { texto: 'Revisada', clase: 'bg-emerald-600 text-white' },
  descartada: { texto: 'Descartada', clase: 'bg-slate-400 text-white' },
};

/** "Últimas sugerencias" (presentational): author, date, state and text, newest first */
@Component({
  selector: 'app-sugerencias-lista',
  imports: [DatePipe],
  template: `
    @for (s of sugerencias(); track s.id) {
      <article class="tarjeta mb-2 p-3">
        <p class="flex flex-wrap items-center gap-2 text-sm">
          <strong>{{ s.autor }}</strong>
          <span class="text-xs text-slate-500">{{ s.fecha | date: 'dd/MM/yyyy HH:mm' }}</span>
          <span class="chip" [class]="estado(s.estado).clase">{{ estado(s.estado).texto }}</span>
        </p>
        <p class="mt-1 whitespace-pre-line text-sm">{{ s.texto }}</p>
      </article>
    } @empty {
      <p class="text-sm text-slate-500">Todavía no hay sugerencias.</p>
    }
  `,
})
export class SugerenciasListaComponent {
  readonly sugerencias = input<Sugerencia[]>([]);

  protected estado(valor: string): { texto: string; clase: string } {
    return ESTADOS[valor] ?? { texto: valor.charAt(0).toUpperCase() + valor.slice(1), clase: 'bg-slate-400 text-white' };
  }
}
