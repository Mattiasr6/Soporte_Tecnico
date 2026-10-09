import { DatePipe } from '@angular/common';
import { Component, computed, effect, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Ambiente, Atencion } from '../../core/modelos';
import { TIPOS_TICKET } from '../../core/tickets';

/** Copies allowed per lab, as in Django's clone screen */
export const MAX_COPIAS_POR_LAB = 99;

/** What the page needs to create the copies */
export interface DatosClonado {
  descripcion: string;
  solucion: string;
  prioridad: number;
  /** Lab id repeated once per copy */
  laboratorios: number[];
}

/**
 * Clone form (presentational), like Django's `laboratorios_clonar.html`: the
 * texts of the copies can be edited first, and each lab gets how many copies
 * of the attention to create (several in the same lab are allowed).
 * Copies are lab-level tickets: the PCs of the original belong to its own lab.
 */
@Component({
  selector: 'app-clonar-atencion',
  imports: [FormsModule, DatePipe],
  template: `
    @let o = origen();
    <form class="space-y-3" [id]="formId()" (ngSubmit)="enviar()">
      <div class="rounded-lg bg-slate-50 p-3 text-sm">
        <p><span class="text-slate-500">Origen:</span> <b>#{{ o.id }}</b> · {{ tipo() }} · {{ o.ambiente?.codigo || 'Sin lab' }} · {{ o.creado_en | date: 'dd/MM/yyyy HH:mm' }}</p>
        <p class="mt-0.5 text-slate-600">Edita lo que quieras antes de crear las copias.</p>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="clon-desc">Descripción *</label>
          <textarea id="clon-desc" class="campo" rows="3" maxlength="500" [(ngModel)]="descripcion" name="descripcion"></textarea>
        </div>
        <div>
          <label class="etiqueta" for="clon-sol">Solución</label>
          <textarea id="clon-sol" class="campo" rows="3" maxlength="1000" [(ngModel)]="solucion" name="solucion"></textarea>
        </div>
      </div>
      <div class="flex items-center gap-2 text-sm">
        <label class="text-slate-600" for="clon-prioridad">Prioridad</label>
        <select id="clon-prioridad" class="campo !w-32 !py-1" [(ngModel)]="prioridad" name="prioridad">
          <option [ngValue]="1">Alta</option><option [ngValue]="2">Media</option><option [ngValue]="3">Baja</option>
        </select>
      </div>
      <fieldset>
        <legend class="etiqueta">Clonar en… <span class="font-normal text-slate-400">(cuántas copias por laboratorio; pueden ser varias del mismo)</span></legend>
        <div class="flex flex-wrap gap-1.5">
          @for (lab of laboratorios(); track lab.id) {
            <label class="flex items-center gap-1.5 rounded-lg border-2 px-2 py-1 text-sm font-semibold transition"
                   [class]="(copias()[lab.id] ?? 0) > 0 ? 'border-marca-500 bg-marca-50 text-marca-700' : 'border-slate-200'"
                   [style.border-left]="'5px solid ' + lab.color">
              {{ lab.codigo }}
              <input type="number" class="campo !w-16 !px-1.5 !py-0.5" min="0" [max]="maxCopias" [ngModel]="copias()[lab.id] ?? 0"
                     (ngModelChange)="fijarCopias(lab.id, $event)" [name]="'copias-' + lab.id" [attr.aria-label]="'Copias en ' + lab.codigo">
            </label>
          } @empty {
            <p class="text-sm text-slate-500">Sin laboratorios activos.</p>
          }
        </div>
        <p class="mt-1 text-xs" [class]="total() ? 'text-marca-700' : 'text-slate-400'">
          {{ total() === 0 ? 'Pon cuántas copias quieres en al menos un laboratorio.' : total() === 1 ? 'Se creará 1 copia.' : 'Se crearán ' + total() + ' copias.' }}
        </p>
      </fieldset>
    </form>
  `,
})
export class ClonarAtencionComponent {
  readonly origen = input.required<Atencion>();
  readonly laboratorios = input<Ambiente[]>([]);
  /** Id of the <form>, so the modal footer button can submit it */
  readonly formId = input('form-clonar');
  readonly confirmar = output<DatosClonado>();
  /** Validation message for the page to show */
  readonly aviso = output<string>();

  protected readonly maxCopias = MAX_COPIAS_POR_LAB;
  protected descripcion = '';
  protected solucion = '';
  protected prioridad = 2;
  protected readonly copias = signal<Record<number, number>>({});
  protected readonly tipo = computed(() => TIPOS_TICKET[this.origen().tipo]?.texto ?? this.origen().tipo);
  protected readonly total = computed(() => Object.values(this.copias()).reduce((s, n) => s + n, 0));

  constructor() {
    // A new origin resets the form with its texts
    effect(() => {
      const o = this.origen();
      this.descripcion = o.descripcion;
      this.solucion = o.solucion ?? '';
      this.prioridad = o.prioridad ?? 2;
      this.copias.set({});
    });
  }

  protected fijarCopias(labId: number, valor: number | string | null): void {
    const n = Math.min(Math.max(Math.trunc(Number(valor) || 0), 0), MAX_COPIAS_POR_LAB);
    this.copias.update((c) => ({ ...c, [labId]: n }));
  }

  protected enviar(): void {
    if (this.descripcion.trim().length < 3) return this.aviso.emit('Escribe la descripción de las copias.');
    if (!this.total()) return this.aviso.emit('Pon cuántas copias quieres en al menos un laboratorio.');
    const laboratorios = Object.entries(this.copias()).flatMap(([id, n]) => Array<number>(n).fill(Number(id)));
    this.confirmar.emit({ descripcion: this.descripcion.trim(), solucion: this.solucion.trim(), prioridad: this.prioridad, laboratorios });
  }
}
