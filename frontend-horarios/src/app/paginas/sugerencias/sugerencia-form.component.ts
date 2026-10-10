import { Component, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAXIMO_SUGERENCIA } from '../../core/sugerencias.service';

/** New suggestion form (presentational); the container clears it through `limpiar` after a send */
@Component({
  selector: 'app-sugerencia-form',
  imports: [FormsModule],
  template: `
    <form class="tarjeta p-4" (ngSubmit)="enviarTexto()">
      <label class="etiqueta" for="sugerencia-texto">Tu sugerencia</label>
      <textarea class="campo" id="sugerencia-texto" name="texto" rows="4" [maxlength]="maximo" required
                placeholder="Escribí tu sugerencia…" [ngModel]="texto()" (ngModelChange)="texto.set($event)"></textarea>
      <p class="mt-1 text-xs text-slate-500">Máximo {{ maximo }} caracteres.</p>
      <button class="btn-primario mt-2" type="submit" [disabled]="enviando() || !texto().trim()">Enviar</button>
    </form>
  `,
})
export class SugerenciaFormComponent {
  readonly enviando = input(false);
  /** Trimmed text to send */
  readonly enviar = output<string>();

  protected readonly maximo = MAXIMO_SUGERENCIA;
  protected readonly texto = signal('');

  protected enviarTexto(): void {
    const texto = this.texto().trim();
    if (texto) this.enviar.emit(texto);
  }

  /** Empties the textarea (called by the container once the API accepted the text) */
  limpiar(): void {
    this.texto.set('');
  }
}
