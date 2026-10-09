import { Component, computed, input } from '@angular/core';
import { DIAS_CUSTODIA, EstadoObjetoVisible } from '../../core/objetos';

const ESTILOS: Record<EstadoObjetoVisible, { texto: string; clase: string }> = {
  en_custodia: { texto: 'En custodia', clase: 'bg-amber-500 text-white' },
  entregado: { texto: 'Entregado', clase: 'bg-emerald-600 text-white' },
  vencido: { texto: 'Vencido', clase: 'bg-rose-600 text-white' },
};

/** State chip of a lost object (presentational), including the computed "vencido" */
@Component({
  selector: 'app-objeto-estado-chip',
  host: { class: 'contents' },
  template: `<span class="chip" [class]="estilo().clase" [attr.title]="titulo()">{{ estilo().texto }}</span>`,
})
export class ObjetoEstadoChipComponent {
  readonly estado = input.required<EstadoObjetoVisible>();

  protected readonly estilo = computed(() => ESTILOS[this.estado()]);
  protected readonly titulo = computed(() =>
    this.estado() === 'vencido' ? `Más de ${DIAS_CUSTODIA} días en custodia; aún se puede entregar` : null);
}
