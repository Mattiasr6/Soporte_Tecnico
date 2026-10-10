import { Component, effect, input, output, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AnuncioEquipo } from '../../core/inicio-soporte.service';

/** Max length of the announcement textarea (Django `maxlength="300"`) */
const MAXIMO_ANUNCIO = 300;

/**
 * "Anuncio del equipo" (presentational). Everyone reads it; who may publish
 * (`puedeEditar`) gets the textarea with Publicar / Borrar instead. A refresh
 * never overwrites the text while it is being typed.
 */
@Component({
  selector: 'app-anuncio-equipo',
  imports: [FormsModule],
  template: `
    @if (puedeEditar()) {
      <form (ngSubmit)="publicar.emit(borrador().trim())">
        <textarea class="campo" rows="2" [maxlength]="maximo" name="anuncio" aria-label="Anuncio del equipo"
                  placeholder="Un aviso para el equipo (corte de red, algo que llegó, recordatorio)…"
                  [ngModel]="borrador()" (ngModelChange)="borrador.set($event)"
                  (focus)="escribiendo.set(true)" (blur)="escribiendo.set(false)"></textarea>
        <div class="mt-2 flex flex-wrap items-center gap-2">
          <button type="submit" class="btn-primario btn-sm" [disabled]="guardando()">Publicar</button>
          @if (anuncio()?.message) {
            <button type="button" class="btn-fantasma btn-sm" [disabled]="guardando()" (click)="publicar.emit('')">Borrar</button>
          }
          @if (aviso()) {
            <span class="text-xs" [class]="avisoError() ? 'text-red-700' : 'text-slate-500'">{{ aviso() }}</span>
          }
        </div>
      </form>
    } @else if (anuncio()?.message) {
      <p class="whitespace-pre-line">{{ anuncio()!.message }}</p>
    } @else {
      <p class="text-sm text-slate-500">No hay anuncios por ahora.</p>
    }
  `,
})
export class AnuncioEquipoComponent {
  readonly anuncio = input<AnuncioEquipo | null>(null);
  /** Jefe or dashboard users (Django `can_dashboard`) */
  readonly puedeEditar = input(false);
  readonly guardando = input(false);
  /** Result line next to the buttons ("Publicado ✓" or the error) */
  readonly aviso = input('');
  readonly avisoError = input(false);
  /** Message to publish; empty deletes the announcement */
  readonly publicar = output<string>();

  protected readonly maximo = MAXIMO_ANUNCIO;
  protected readonly borrador = signal('');
  protected readonly escribiendo = signal(false);

  constructor() {
    // Mirror the published text into the textarea unless the user is typing (Django `pintarAnuncio`).
    effect(() => {
      const mensaje = this.anuncio()?.message ?? '';
      if (!untracked(this.escribiendo)) this.borrador.set(mensaje);
    });
  }
}
