import { Component, computed, input } from '@angular/core';
import { etiquetaPresencia } from '../../core/inicio-soporte.service';

/** Chip color per presence state; unknown states use the neutral one */
const CLASE_ESTADO: Record<string, string> = {
  disponible: 'bg-emerald-600 text-white',
  ocupado: 'bg-amber-500 text-white',
  extraturno: 'bg-sky-600 text-white',
  ausente: 'bg-slate-400 text-white',
};

/** Presence state chip of a Soporte user (presentational) */
@Component({
  selector: 'app-estado-presencia-chip',
  host: { class: 'contents' },
  template: `<span class="chip whitespace-nowrap" [class]="clase()">{{ texto() }}</span>`,
})
export class EstadoPresenciaChipComponent {
  readonly estado = input.required<string>();

  protected readonly clase = computed(() => CLASE_ESTADO[this.estado()] ?? CLASE_ESTADO['ausente']);
  protected readonly texto = computed(() => etiquetaPresencia(this.estado()));
}
