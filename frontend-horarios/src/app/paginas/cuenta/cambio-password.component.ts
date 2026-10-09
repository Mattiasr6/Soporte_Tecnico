import { Component, computed, effect, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MINIMO_PASSWORD } from '../../core/cuenta.service';

/** Data the form emits once it is valid */
export interface CambioPassword {
  actual: string;
  nueva: string;
}

/**
 * Formulario de cambio de contraseña (presentacional): valida largo mínimo y que
 * las dos nuevas coincidan, y emite `cambiar`. La página hace la llamada.
 */
@Component({
  selector: 'app-cambio-password',
  imports: [FormsModule],
  template: `
    <form class="space-y-3" (ngSubmit)="enviar()">
      <div>
        <label class="etiqueta" for="perfil-actual">Contraseña actual</label>
        <input class="campo" id="perfil-actual" name="actual" type="password" autocomplete="current-password" required
               [ngModel]="actual()" (ngModelChange)="actual.set($event)">
      </div>
      <div>
        <label class="etiqueta" for="perfil-nueva">Contraseña nueva</label>
        <input class="campo" id="perfil-nueva" name="nueva" type="password" autocomplete="new-password" required [minlength]="minimo"
               [ngModel]="nueva()" (ngModelChange)="nueva.set($event)">
      </div>
      <div>
        <label class="etiqueta" for="perfil-repetir">Repetir la nueva</label>
        <input class="campo" id="perfil-repetir" name="repetir" type="password" autocomplete="new-password" required [minlength]="minimo"
               [ngModel]="repetir()" (ngModelChange)="repetir.set($event)">
      </div>
      @if (error()) {
        <p class="text-sm text-red-700">{{ error() }}</p>
      } @else {
        <p class="text-xs text-slate-500">Mínimo {{ minimo }} caracteres.</p>
      }
      <button class="btn-primario" type="submit" [disabled]="enviando() || !completo()">
        {{ enviando() ? 'Cambiando…' : 'Cambiar contraseña' }}
      </button>
    </form>
  `,
})
export class CambioPasswordComponent {
  /** true while the page is calling the API */
  readonly enviando = input(false);
  /** Bumped by the page after a successful change to clear the fields */
  readonly reinicio = input(0);
  readonly cambiar = output<CambioPassword>();

  protected readonly minimo = MINIMO_PASSWORD;
  protected readonly actual = signal('');
  protected readonly nueva = signal('');
  protected readonly repetir = signal('');
  protected readonly error = signal('');
  protected readonly completo = computed(() => !!this.actual() && !!this.nueva() && !!this.repetir());

  constructor() {
    effect(() => {
      this.reinicio();
      this.actual.set('');
      this.nueva.set('');
      this.repetir.set('');
      this.error.set('');
    });
  }

  protected enviar(): void {
    if (this.nueva().length < MINIMO_PASSWORD) {
      this.error.set(`La contraseña nueva necesita al menos ${MINIMO_PASSWORD} caracteres.`);
    } else if (this.nueva() !== this.repetir()) {
      this.error.set('Las dos contraseñas nuevas no coinciden.');
    } else {
      this.error.set('');
      this.cambiar.emit({ actual: this.actual(), nueva: this.nueva() });
    }
  }
}
