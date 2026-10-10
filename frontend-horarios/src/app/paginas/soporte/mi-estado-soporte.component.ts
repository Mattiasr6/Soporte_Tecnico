import { Component, computed, input, output } from '@angular/core';
import { UsuarioPresencia } from '../../core/inicio-soporte.service';
import { EstadoPresenciaChipComponent } from './estado-presencia-chip.component';

/**
 * "Mi estado" of the Soporte home (presentational): my chip and the button that
 * swaps disponible ↔ ocupado. Off shift the state is computed, so the button is
 * disabled and the reason is shown (Django `inicio.html`).
 */
@Component({
  selector: 'app-mi-estado-soporte',
  imports: [EstadoPresenciaChipComponent],
  template: `
    @if (yo(); as y) {
      <div class="flex flex-wrap items-center gap-2">
        <app-estado-presencia-chip [estado]="y.estado_actual" />
        <button type="button" class="btn-secundario btn-sm" [disabled]="!y.puede_cambiar_estado || guardando()" (click)="cambiar.emit(siguiente())">
          {{ textoBoton() }}
        </button>
      </div>
      @if (!y.puede_cambiar_estado) {
        <p class="mt-1 text-xs text-slate-500">
          Estás fuera de turno{{ y.entra_a_las ? ' hasta las ' + y.entra_a_las : '' }}. Tu estado se calcula solo, no hace falta que lo toques.
        </p>
      }
    }
  `,
})
export class MiEstadoSoporteComponent {
  readonly yo = input<UsuarioPresencia | null>(null);
  /** A state change is in flight */
  readonly guardando = input(false);
  /** New state requested by the button */
  readonly cambiar = output<'disponible' | 'ocupado'>();

  /** Django: from disponible you go ocupado; from anything else, disponible */
  protected readonly siguiente = computed(() => (this.yo()?.estado_actual === 'disponible' ? 'ocupado' : 'disponible'));
  protected readonly textoBoton = computed(() => {
    const estado = this.yo()?.estado_actual;
    if (estado === 'ocupado') return 'Ponerme disponible';
    if (estado === 'disponible') return 'Ponerme ocupado';
    return 'Marcarme disponible';
  });
}
