import { Component, effect, input, output, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Ambiente, FichaLaboratorio } from '../../core/modelos';

type CampoTexto = 'procesador' | 'ram' | 'almacenamiento' | 'marca' | 'gpu' | 'monitores';
type CampoNumero = 'sillas' | 'capacidad' | 'pcs_estudiantes' | 'pcs_docentes';

const TEXTOS: { clave: CampoTexto; etiqueta: string; max: number }[] = [
  { clave: 'procesador', etiqueta: 'Procesador', max: 200 },
  { clave: 'ram', etiqueta: 'RAM', max: 100 },
  { clave: 'almacenamiento', etiqueta: 'Disco', max: 100 },
  { clave: 'marca', etiqueta: 'Marca', max: 100 },
  { clave: 'gpu', etiqueta: 'GPU', max: 100 },
  { clave: 'monitores', etiqueta: 'Monitores', max: 100 },
];

const NUMEROS: { clave: CampoNumero; etiqueta: string }[] = [
  { clave: 'sillas', etiqueta: 'Sillas' },
  { clave: 'capacidad', etiqueta: 'Capacidad' },
  { clave: 'pcs_estudiantes', etiqueta: 'PCs estudiantes' },
  { clave: 'pcs_docentes', etiqueta: 'PCs docentes' },
];

/** Empty draft value for an input: '' for blank, the number or text otherwise */
type Borrador = Record<CampoTexto | CampoNumero, string | number | null>;

function borradorDe(a: Ambiente | undefined): Borrador {
  return {
    procesador: a?.procesador ?? '',
    ram: a?.ram ?? '',
    almacenamiento: a?.almacenamiento ?? '',
    marca: a?.marca ?? '',
    gpu: a?.gpu ?? '',
    monitores: a?.monitores ?? '',
    sillas: a?.sillas ?? null,
    capacidad: a?.capacidad ?? null,
    pcs_estudiantes: a?.pcs_estudiantes ?? null,
    pcs_docentes: a?.pcs_docentes ?? null,
  };
}

function numero(v: string | number | null): number | null {
  if (v === null || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

/**
 * Lab hardware sheet ("Ficha del lab", Django `laboratorios_pcs.html`), presentational.
 * Shows the declared standard spec of the lab; with `puedeEditar` it opens an inline
 * form and emits the whole sheet (blank = cleared; a blank capacidad keeps the current one).
 * `inventarioEstudiantes` / `inventarioDocentes` are the PCs really registered, shown as a hint.
 */
@Component({
  selector: 'app-ficha-laboratorio',
  imports: [FormsModule],
  template: `
    <section class="rounded-xl border border-slate-200 p-4">
      <div class="mb-3 flex items-center justify-between gap-2">
        <h3 class="text-sm font-semibold text-slate-700">Ficha del laboratorio</h3>
        @if (puedeEditar() && !editando()) {
          <button type="button" class="btn-secundario btn-sm" (click)="editar()">Editar ficha</button>
        }
      </div>

      @if (editando()) {
        <form class="grid gap-3 sm:grid-cols-2" (ngSubmit)="enviar()" id="form-ficha-lab">
          @for (c of textos; track c.clave) {
            <label class="block text-xs text-slate-500">{{ c.etiqueta }}
              <input class="campo mt-1" type="text" [name]="c.clave" [maxlength]="c.max" [(ngModel)]="borrador[c.clave]" />
            </label>
          }
          @for (c of numeros; track c.clave) {
            <label class="block text-xs text-slate-500">{{ c.etiqueta }}
              <input class="campo mt-1" type="number" min="0" step="1" [name]="c.clave" [(ngModel)]="borrador[c.clave]" />
            </label>
          }
          <p class="text-[11px] text-slate-400 sm:col-span-2">Un campo vacío se borra de la ficha; la capacidad vacía conserva la actual. Inventario registrado: {{ inventarioEstudiantes() }} PCs de estudiantes y {{ inventarioDocentes() }} de docente.</p>
          <div class="flex justify-end gap-2 sm:col-span-2">
            <button type="button" class="btn-secundario btn-sm" (click)="editando.set(false)" [disabled]="guardando()">Cancelar</button>
            <button type="submit" class="btn-primario btn-sm" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Guardar ficha' }}</button>
          </div>
        </form>
      } @else {
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
          @for (c of textos; track c.clave) {
            <div><dt class="text-[11px] text-slate-400">{{ c.etiqueta }}</dt><dd class="truncate" [title]="ambiente()?.[c.clave] ?? ''">{{ ambiente()?.[c.clave] || '—' }}</dd></div>
          }
          @for (c of numeros; track c.clave) {
            <div>
              <dt class="text-[11px] text-slate-400">{{ c.etiqueta }}</dt>
              <dd>
                {{ ambiente()?.[c.clave] ?? '—' }}
                @if (c.clave === 'pcs_estudiantes') { <span class="text-[11px] text-slate-400">(inventario {{ inventarioEstudiantes() }})</span> }
                @if (c.clave === 'pcs_docentes') { <span class="text-[11px] text-slate-400">(inventario {{ inventarioDocentes() }})</span> }
              </dd>
            </div>
          }
        </dl>
      }
    </section>
  `,
})
export class FichaLaboratorioComponent {
  readonly ambiente = input<Ambiente | undefined>();
  readonly puedeEditar = input(false);
  readonly guardando = input(false);
  readonly inventarioEstudiantes = input(0);
  readonly inventarioDocentes = input(0);
  readonly guardar = output<FichaLaboratorio>();

  protected readonly textos = TEXTOS;
  protected readonly numeros = NUMEROS;
  protected readonly editando = signal(false);
  protected borrador: Borrador = borradorDe(undefined);

  constructor() {
    // Another lab (or a saved sheet) closes the form
    effect(() => {
      this.ambiente();
      untracked(() => this.editando.set(false));
    });
  }

  protected editar(): void {
    this.borrador = borradorDe(this.ambiente());
    this.editando.set(true);
  }

  protected enviar(): void {
    const b = this.borrador;
    const texto = (v: string | number | null) => (v === null ? null : String(v).trim() || null);
    this.guardar.emit({
      procesador: texto(b.procesador),
      ram: texto(b.ram),
      almacenamiento: texto(b.almacenamiento),
      marca: texto(b.marca),
      gpu: texto(b.gpu),
      monitores: texto(b.monitores),
      sillas: numero(b.sillas),
      capacidad: numero(b.capacidad),
      pcs_estudiantes: numero(b.pcs_estudiantes),
      pcs_docentes: numero(b.pcs_docentes),
    });
  }
}
