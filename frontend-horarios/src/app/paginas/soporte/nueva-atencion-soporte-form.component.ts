import { Component, effect, input, output, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ItemBorradorSoporte } from '../../core/borrador-soporte.service';
import { hoyIso } from '../../core/fechas';
import {
  CATEGORIAS_SOPORTE, MEDIOS_SOPORTE, SOLICITANTES_SOPORTE, UsuarioSoporte,
} from '../../core/soporte.service';
import { claveDestino, DestinoSoporte, SelectorAreaSoporteComponent } from './selector-area-soporte.component';

/** "Registrar" request: the form row when the list is empty, otherwise the list */
export interface PedidoRegistro {
  /** Validated form row, only when the list is empty */
  directo: ItemBorradorSoporte | null;
  /** The list is sent while the form holds text that was not added to it */
  formularioConDatos: boolean;
}

/** Quick templates of the Django form: categoría, descripción, solución */
const PLANTILLAS: { etiqueta: string; categoria: string; descripcion: string; solucion: string }[] = [
  { etiqueta: 'Conectividad', categoria: 'Redes/Conectividad', descripcion: 'Sin conectividad en puerto', solucion: 'Se validó enlace y switch' },
  { etiqueta: 'Acceso', categoria: 'Cuentas/Accesos', descripcion: 'Sin acceso a plataforma', solucion: 'Se restableció acceso' },
  { etiqueta: 'Hardware', categoria: 'Hardware', descripcion: 'Equipo no enciende', solucion: 'Se revisó fuente y conexiones' },
  { etiqueta: 'Software', categoria: 'Software', descripcion: 'Falla aplicación', solucion: 'Se reinstaló componente' },
];

/**
 * Formulario de nueva atención de Soporte (presentacional). Mismos campos,
 * valores por defecto y validaciones que Django `_item_nueva_desde_post`:
 * área o dependencia, medio (Interno), solicitante (ADM), categoría,
 * descripción, solución, observaciones y enlace opcionales, colaborador
 * (nunca uno mismo) y fecha (hoy).
 */
@Component({
  selector: 'app-nueva-atencion-soporte-form',
  imports: [FormsModule, SelectorAreaSoporteComponent],
  template: `
    <form class="space-y-3" (ngSubmit)="agregarALista()">
      @if (editando() !== null) {
        <p class="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Editando la atención #{{ editando()! + 1 }} de la lista.
          <button class="btn-fantasma btn-sm" type="button" (click)="cancelarEdicion.emit()">Cancelar edición</button>
        </p>
      }
      <div>
        <app-selector-area-soporte idCampo="na-area" [destinos]="destinos()" [(seleccion)]="destino" />
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <fieldset>
          <legend class="etiqueta">Medio</legend>
          <div class="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Medio de solicitud">
            @for (m of medios; track m) {
              <label class="chip cursor-pointer border" [class]="medio() === m ? 'border-marca-500 bg-marca-100 text-marca-700' : 'border-slate-200 text-slate-600'">
                <input class="sr-only" type="radio" name="medio" [value]="m" [checked]="medio() === m" (change)="medio.set(m)"> {{ m }}
              </label>
            }
          </div>
        </fieldset>
        <div>
          <label class="etiqueta" for="na-solicitante">Solicitante</label>
          <select class="campo" id="na-solicitante" name="solicitante" [ngModel]="solicitante()" (ngModelChange)="solicitante.set($event)">
            @for (s of solicitantes; track s) { <option [value]="s">{{ s }}</option> }
          </select>
        </div>
      </div>
      <fieldset>
        <legend class="etiqueta">Categoría</legend>
        <div class="flex flex-wrap gap-1.5">
          @for (c of categorias; track c) {
            <label class="chip cursor-pointer border" [class]="categoria() === c ? 'border-marca-500 bg-marca-100 text-marca-700' : 'border-slate-200 text-slate-600'">
              <input class="sr-only" type="radio" name="categoria" [value]="c" [checked]="categoria() === c" (change)="categoria.set(c)"> {{ c }}
            </label>
          }
        </div>
      </fieldset>
      <div class="flex flex-wrap items-center gap-1.5 text-xs">
        <span class="text-slate-500">Plantillas:</span>
        @for (p of plantillas; track p.etiqueta) {
          <button class="btn-secundario btn-sm" type="button" (click)="usarPlantilla(p)">{{ p.etiqueta }}</button>
        }
      </div>
      <div>
        <label class="etiqueta" for="na-desc">Descripción</label>
        <textarea class="campo" id="na-desc" name="descripcion" rows="3" [ngModel]="descripcion()" (ngModelChange)="descripcion.set($event)"></textarea>
      </div>
      <div>
        <label class="etiqueta" for="na-sol">Solución</label>
        <textarea class="campo" id="na-sol" name="solucion" rows="3" [ngModel]="solucion()" (ngModelChange)="solucion.set($event)"></textarea>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="conObs" [ngModel]="conObservaciones()" (ngModelChange)="conObservaciones.set($event)"> Agregar observaciones
          </label>
          @if (conObservaciones()) {
            <input class="campo mt-1" name="observaciones" aria-label="Observaciones" [ngModel]="observaciones()" (ngModelChange)="observaciones.set($event)">
          }
        </div>
        <div>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="conEnlace" [ngModel]="conEnlace()" (ngModelChange)="conEnlace.set($event)"> Agregar enlace de apoyo
          </label>
          @if (conEnlace()) {
            <input class="campo mt-1" name="enlace" aria-label="Enlace de apoyo" placeholder="https://intranet..." [ngModel]="enlace()" (ngModelChange)="enlace.set($event)">
          }
        </div>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="na-col">Colaborador (opcional)</label>
          <select class="campo" id="na-col" name="colaborador" [ngModel]="colaborador()" (ngModelChange)="colaborador.set($event)">
            <option [ngValue]="null">— Sin colaborador —</option>
            @for (u of usuarios(); track u.id) { <option [ngValue]="u.id">{{ u.display_name }}</option> }
          </select>
        </div>
        <div>
          <label class="etiqueta" for="na-fec">Fecha</label>
          <input class="campo" id="na-fec" name="fecha" type="date" [ngModel]="fecha()" (ngModelChange)="fecha.set($event)">
        </div>
      </div>
      @if (error()) { <p class="text-sm text-red-700" role="alert">{{ error() }}</p> }
      <footer class="flex flex-wrap gap-2 border-t border-slate-200 pt-3">
        <button class="btn-primario" type="button" [disabled]="enviando()" (click)="registrar()">
          {{ enviando() ? 'Registrando…' : cantidadLista() ? 'Registrar las ' + cantidadLista() + ' atenciones' : 'Registrar la atención' }}
        </button>
        <button [class]="editando() !== null ? 'btn-primario' : 'btn-secundario'" type="submit" [disabled]="enviando()">
          {{ editando() !== null ? 'Guardar cambios' : 'Agregar a la lista' }}
        </button>
      </footer>
    </form>
  `,
})
export class NuevaAtencionSoporteFormComponent {
  readonly destinos = input<DestinoSoporte[]>([]);
  /** Possible collaborators, without the current user */
  readonly usuarios = input<UsuarioSoporte[]>([]);
  readonly miUsuarioId = input<number | null>(null);
  /** Row loaded in the form when editing a list item */
  readonly inicial = input<ItemBorradorSoporte | null>(null);
  /** Index of the list row being edited, or null */
  readonly editando = input<number | null>(null);
  readonly cantidadLista = input(0);
  readonly enviando = input(false);

  readonly agregar = output<ItemBorradorSoporte>();
  readonly registrarPedido = output<PedidoRegistro>();
  readonly cancelarEdicion = output<void>();

  protected readonly categorias = CATEGORIAS_SOPORTE;
  protected readonly medios = MEDIOS_SOPORTE;
  protected readonly solicitantes = SOLICITANTES_SOPORTE;
  protected readonly plantillas = PLANTILLAS;

  protected readonly destino = signal<DestinoSoporte | null>(null);
  protected readonly medio = signal('Interno');
  protected readonly solicitante = signal('ADM');
  protected readonly categoria = signal('');
  protected readonly descripcion = signal('');
  protected readonly solucion = signal('');
  protected readonly conObservaciones = signal(false);
  protected readonly observaciones = signal('');
  protected readonly conEnlace = signal(false);
  protected readonly enlace = signal('');
  protected readonly colaborador = signal<number | null>(null);
  protected readonly fecha = signal(hoyIso());
  protected readonly error = signal('');

  constructor() {
    // Load the edited row (or a blank form) whenever the edited row changes
    effect(() => {
      const item = this.inicial();
      const destinos = this.destinos();
      untracked(() => this.cargar(item, destinos));
    });
  }

  protected usarPlantilla(p: (typeof PLANTILLAS)[number]): void {
    this.categoria.set(p.categoria);
    this.descripcion.set(p.descripcion);
    this.solucion.set(p.solucion);
  }

  protected agregarALista(): void {
    const item = this.validar();
    if (!item) return;
    this.agregar.emit(item);
    this.cargar(null, this.destinos());
  }

  protected registrar(): void {
    if (this.cantidadLista() > 0) {
      const conDatos = this.editando() === null && !!(this.descripcion().trim() || this.solucion().trim());
      this.registrarPedido.emit({ directo: null, formularioConDatos: conDatos });
      return;
    }
    const item = this.validar();
    if (item) this.registrarPedido.emit({ directo: item, formularioConDatos: false });
  }

  /** Same checks and messages as Django `_item_nueva_desde_post` */
  private validar(): ItemBorradorSoporte | null {
    const destino = this.destino();
    const descripcion = this.descripcion().trim();
    const solucion = this.solucion().trim();
    const categoria = this.categoria().trim();
    const colaborador = this.colaborador();
    let error = '';
    if (!destino) error = 'Elegí un área o dependencia.';
    else if (!descripcion || !solucion || !categoria) error = 'Faltan descripción, solución o categoría.';
    else if (colaborador !== null && colaborador === this.miUsuarioId()) error = 'No podés ser tu propio colaborador.';
    this.error.set(error);
    if (error || !destino) return null;
    return {
      ruta: destino.ruta,
      area_solicitante: '',
      grupo_padre_id: destino.grupo_padre_id,
      grupo_id: destino.grupo_id,
      area_id: destino.area_id,
      medio_solicitud: this.medio() || 'Interno',
      usuario_solicitante: this.solicitante() || 'ADM',
      categoria,
      descripcion,
      solucion,
      observaciones: this.conObservaciones() && this.observaciones() ? this.observaciones() : null,
      enlace_apoyo: this.conEnlace() && this.enlace() ? this.enlace() : null,
      colaborador_id: colaborador,
      fecha_registro: this.fecha() || hoyIso(),
    };
  }

  private cargar(item: ItemBorradorSoporte | null, destinos: DestinoSoporte[]): void {
    const clave = item ? claveDestino(item.area_id, item.grupo_id) : '';
    this.destino.set(clave ? (destinos.find((d) => d.clave === clave) ?? null) : null);
    this.medio.set(item?.medio_solicitud ?? 'Interno');
    this.solicitante.set(item?.usuario_solicitante ?? 'ADM');
    this.categoria.set(item?.categoria ?? '');
    this.descripcion.set(item?.descripcion ?? '');
    this.solucion.set(item?.solucion ?? '');
    this.conObservaciones.set(!!item?.observaciones);
    this.observaciones.set(item?.observaciones ?? '');
    this.conEnlace.set(!!item?.enlace_apoyo);
    this.enlace.set(item?.enlace_apoyo ?? '');
    this.colaborador.set(item?.colaborador_id ?? null);
    this.fecha.set(item?.fecha_registro ?? hoyIso());
    this.error.set('');
  }
}
