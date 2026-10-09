import { Component, input, OnDestroy, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconoComponent } from '../../compartido/icono.component';
import { Ambiente, TurnoCodigo } from '../../core/modelos';
import { NovedadNueva } from '../../core/novedades.service';
import { TURNOS_TICKET } from '../../core/tickets';

const MAX_TEXTO = 2000;

/**
 * New novedad form (presentational), like Django's "novedades" form: free
 * text, optional turno (empty = the turno of the current hour), optional lab
 * and optional photo. It only emits what was filled in; the container saves it.
 */
@Component({
  selector: 'app-novedad-form',
  imports: [FormsModule, IconoComponent],
  template: `
    <form class="space-y-3" [id]="idForm()" (ngSubmit)="enviar()">
      <div>
        <label class="etiqueta" for="nov-texto">Novedad *</label>
        <textarea id="nov-texto" class="campo" rows="4" [maxlength]="maxTexto" name="texto"
                  [ngModel]="texto()" (ngModelChange)="texto.set($event)"
                  placeholder="Ej: El proyector del LAB-02 no enciende; se avisó a soporte."></textarea>
        <p class="mt-0.5 text-right text-[11px] text-slate-400">{{ texto().length }}/{{ maxTexto }}</p>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="nov-turno">Turno</label>
          <select id="nov-turno" class="campo" name="turno" [ngModel]="turno()" (ngModelChange)="turno.set($event)">
            <option [ngValue]="null">Automático (por la hora)</option>
            @for (t of turnos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }
          </select>
        </div>
        <div>
          <label class="etiqueta" for="nov-lab">Laboratorio</label>
          <select id="nov-lab" class="campo" name="lab" [ngModel]="ambienteId()" (ngModelChange)="ambienteId.set($event)">
            <option [ngValue]="null">General (sin laboratorio)</option>
            @for (lab of laboratorios(); track lab.id) { <option [ngValue]="lab.id">{{ lab.codigo }}</option> }
          </select>
        </div>
      </div>
      <div>
        <span class="etiqueta">Foto <span class="font-normal text-slate-400">(opcional)</span></span>
        <label class="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 p-3 hover:border-marca-400">
          @if (vista(); as v) {
            <img [src]="v" alt="Vista previa" class="h-20 w-20 rounded-md object-cover">
            <span class="text-sm text-slate-600">Toca para cambiar la foto</span>
          } @else {
            <span class="flex h-20 w-20 items-center justify-center rounded-md bg-slate-100 text-slate-400"><app-icono nombre="camara" [tamano]="26" /></span>
            <span class="text-sm text-slate-600">Tomar o elegir foto</span>
          }
          <input type="file" accept="image/*" capture="environment" class="sr-only" (change)="elegirFoto($event)">
        </label>
        @if (foto()) {
          <button type="button" class="btn-fantasma btn-sm mt-1 text-slate-500" (click)="quitarFoto()">Quitar foto</button>
        }
      </div>
    </form>
  `,
})
export class NovedadFormComponent implements OnDestroy {
  /** Id of the <form>, so the modal footer button can submit it */
  readonly idForm = input('form-novedad');
  readonly laboratorios = input.required<Ambiente[]>();
  readonly guardar = output<NovedadNueva>();

  protected readonly maxTexto = MAX_TEXTO;
  protected readonly turnos = TURNOS_TICKET;
  protected readonly texto = signal('');
  protected readonly turno = signal<TurnoCodigo | null>(null);
  protected readonly ambienteId = signal<number | null>(null);
  protected readonly foto = signal<File | null>(null);
  protected readonly vista = signal<string | null>(null);

  ngOnDestroy(): void {
    this.liberarVista();
  }

  protected elegirFoto(evento: Event): void {
    const archivo = (evento.target as HTMLInputElement).files?.[0] ?? null;
    if (!archivo) return;
    this.liberarVista();
    this.foto.set(archivo);
    this.vista.set(URL.createObjectURL(archivo));
  }

  protected quitarFoto(): void {
    this.liberarVista();
    this.foto.set(null);
  }

  protected enviar(): void {
    this.guardar.emit({
      texto: this.texto().trim(),
      turno: this.turno(),
      ambienteId: this.ambienteId(),
      foto: this.foto(),
    });
  }

  private liberarVista(): void {
    const v = this.vista();
    if (v) URL.revokeObjectURL(v);
    this.vista.set(null);
  }
}
