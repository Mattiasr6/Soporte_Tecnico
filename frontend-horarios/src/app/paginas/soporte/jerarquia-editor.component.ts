import { Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TipoNodo } from '../../core/jerarquia.service';
import { DetalleJerarquia } from './jerarquia-arbol.component';
import { DestinoSoporte, SelectorAreaSoporteComponent } from './selector-area-soporte.component';

export interface RenombreJerarquia {
  nombre: string;
  /** Área only: also rewrite the legacy text of its attentions */
  textoLegado: boolean;
}

export interface NuevoNodoJerarquia {
  tipo: TipoNodo;
  nombre: string;
  /** Null for a sector; required for a dependencia or an área */
  destino: DestinoSoporte | null;
}

const TIPOS: { valor: TipoNodo; texto: string }[] = [
  { valor: 'sector', texto: 'Sector' },
  { valor: 'dependencia', texto: 'Dependencia' },
  { valor: 'area', texto: 'Área' },
];

/**
 * Ficha y acciones de un nodo de la jerarquía (presentacional): renombrar,
 * mover, activar/desactivar, convertir un área en dependencia y eliminar.
 * Sin nodo elegido muestra el alta de sector, dependencia o área. Solo emite;
 * la página confirma y llama a la API.
 */
@Component({
  selector: 'app-jerarquia-editor',
  imports: [FormsModule, SelectorAreaSoporteComponent],
  template: `
    @if (detalle(); as d) {
      <header class="mb-3 flex items-start justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">{{ d.nodo.nombre }}</h2>
          <small class="font-mono text-xs text-slate-500">{{ d.nodo.codigo }}</small>
        </div>
        <button type="button" class="btn-fantasma btn-sm" (click)="cerrar.emit()">Nuevo nodo</button>
      </header>

      <dl class="mb-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt class="text-slate-500">Sector</dt><dd class="font-medium">{{ d.sector.nombre }}</dd>
        <dt class="text-slate-500">Dependencia</dt><dd class="font-medium">{{ d.dependencia?.nombre ?? '— directa del sector' }}</dd>
        @if (d.nodo.tipo !== 'sector') {
          <dt class="text-slate-500">Estado</dt><dd class="font-medium">{{ d.nodo.activo ? 'activa' : 'inactiva' }}</dd>
        }
        <dt class="text-slate-500">Atenciones</dt><dd class="font-medium">{{ d.nodo.total }}</dd>
      </dl>

      <form class="mb-4 space-y-2 border-t border-slate-200 pt-3" (ngSubmit)="enviarNombre()">
        <label class="etiqueta" for="jq-nombre">Nombre</label>
        <input class="campo" id="jq-nombre" name="nombre" required [ngModel]="nombre()" (ngModelChange)="nombre.set($event)">
        @if (d.nodo.tipo === 'area') {
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="textoLegado" [ngModel]="textoLegado()" (ngModelChange)="textoLegado.set($event)">
            Actualizar también el texto de las {{ d.nodo.total }} atenciones
          </label>
        }
        <button class="btn-primario btn-sm" type="submit" [disabled]="ocupado() || !nombre().trim()">Guardar nombre</button>
      </form>

      @if (d.nodo.tipo !== 'sector') {
        <form class="mb-4 space-y-2 border-t border-slate-200 pt-3" (ngSubmit)="enviarMover()">
          <app-selector-area-soporte idCampo="jq-destino" etiqueta="Mover a" placeholder="Escribí para filtrar sectores o dependencias…"
                                     [destinos]="destinosMover()" [(seleccion)]="destino" />
          <p class="text-xs text-amber-700">Se re-apuntarán <b>{{ d.nodo.total }}</b> atenciones al destino nuevo. No se puede deshacer.</p>
          <button class="btn-secundario btn-sm" type="submit" [disabled]="ocupado() || !destinoCambiado()">Mover</button>
        </form>
      }

      <div class="flex flex-wrap gap-2 border-t border-slate-200 pt-3">
        @if (d.nodo.tipo === 'area' && d.nodo.activo) {
          <button type="button" class="btn-secundario btn-sm" [disabled]="ocupado()" (click)="convertir.emit()">Convertir en dependencia</button>
        }
        @if (d.nodo.tipo !== 'sector') {
          <button type="button" class="btn-secundario btn-sm" [disabled]="ocupado()" (click)="alternarActivo.emit()">{{ d.nodo.activo ? 'Desactivar' : 'Activar' }}</button>
        }
        <button type="button" class="btn-peligro btn-sm" [disabled]="ocupado()" (click)="borrar.emit()">Eliminar</button>
      </div>
      <p class="mt-2 text-xs text-slate-500">Solo se elimina si no tiene hijos ni atenciones. Si no, se desactiva.</p>
    } @else {
      <header class="mb-3">
        <h2 class="text-lg font-semibold">Elegí un nodo</h2>
        <p class="text-sm text-slate-500">Hacé clic en un sector, una dependencia o un área del árbol para verlo y editarlo, o creá uno nuevo.</p>
      </header>
      <form class="space-y-3 border-t border-slate-200 pt-3" (ngSubmit)="enviarNuevo()">
        <fieldset>
          <legend class="etiqueta">Nuevo</legend>
          <div class="flex flex-wrap gap-1.5">
            @for (t of tipos; track t.valor) {
              <label class="chip cursor-pointer border" [class]="tipoNuevo() === t.valor ? 'border-marca-500 bg-marca-100 text-marca-700' : 'border-slate-200 text-slate-600'">
                <input class="sr-only" type="radio" name="tipoNuevo" [value]="t.valor" [checked]="tipoNuevo() === t.valor" (change)="elegirTipo(t.valor)"> {{ t.texto }}
              </label>
            }
          </div>
        </fieldset>
        <div>
          <label class="etiqueta" for="jq-nuevo-nombre">Nombre</label>
          <input class="campo" id="jq-nuevo-nombre" name="nombreNuevo" required [placeholder]="'Nombre del ' + (tipoNuevo() === 'area' ? 'área' : tipoNuevo())"
                 [ngModel]="nombreNuevo()" (ngModelChange)="nombreNuevo.set($event)">
        </div>
        @if (tipoNuevo() !== 'sector') {
          <app-selector-area-soporte idCampo="jq-nuevo-destino" etiqueta="Ubicación" placeholder="Escribí para filtrar sectores o dependencias…"
                                     [destinos]="destinosNuevo()" [(seleccion)]="destinoNuevo" />
        }
        <button class="btn-primario btn-sm" type="submit" [disabled]="ocupado() || !puedeCrear()">Crear</button>
      </form>
    }
  `,
})
export class JerarquiaEditorComponent {
  readonly detalle = input<DetalleJerarquia | null>(null);
  /** Every sector as a destination (`s<id>`) */
  readonly destinosSector = input<DestinoSoporte[]>([]);
  /** Every dependencia as a destination (`g<id>`) */
  readonly destinosDependencia = input<DestinoSoporte[]>([]);
  readonly ocupado = input(false);

  readonly renombrar = output<RenombreJerarquia>();
  readonly mover = output<DestinoSoporte>();
  readonly alternarActivo = output<void>();
  readonly convertir = output<void>();
  readonly borrar = output<void>();
  readonly crear = output<NuevoNodoJerarquia>();
  /** Leave the node: back to the create form */
  readonly cerrar = output<void>();

  protected readonly tipos = TIPOS;

  protected readonly nombre = linkedSignal(() => this.detalle()?.nodo.nombre ?? '');
  protected readonly textoLegado = linkedSignal(() => (this.detalle(), false));

  /** A dependencia only moves between sectors; an área also into a dependencia */
  protected readonly destinosMover = computed(() =>
    this.detalle()?.nodo.tipo === 'area' ? [...this.destinosSector(), ...this.destinosDependencia()] : this.destinosSector(),
  );
  /** Current place of the node (Django `_destino_actual`) */
  private readonly destinoActual = computed(() => {
    const d = this.detalle();
    if (!d) return null;
    const clave = d.nodo.tipo === 'area' && d.dependencia ? `g${d.dependencia.id}` : `s${d.sector.id}`;
    return this.destinosMover().find((x) => x.clave === clave) ?? null;
  });
  protected readonly destino = linkedSignal(() => this.destinoActual());
  protected readonly destinoCambiado = computed(() => !!this.destino() && this.destino()?.clave !== this.destinoActual()?.clave);

  protected readonly tipoNuevo = signal<TipoNodo>('sector');
  protected readonly nombreNuevo = signal('');
  protected readonly destinoNuevo = signal<DestinoSoporte | null>(null);
  protected readonly destinosNuevo = computed(() =>
    this.tipoNuevo() === 'area' ? [...this.destinosSector(), ...this.destinosDependencia()] : this.destinosSector(),
  );
  protected readonly puedeCrear = computed(() => !!this.nombreNuevo().trim() && (this.tipoNuevo() === 'sector' || !!this.destinoNuevo()));

  protected elegirTipo(t: TipoNodo): void {
    this.tipoNuevo.set(t);
    // A dependencia cannot live inside another dependencia
    if (t !== 'area' && this.destinoNuevo()?.clave.startsWith('g')) this.destinoNuevo.set(null);
  }

  protected enviarNombre(): void {
    const nombre = this.nombre().trim();
    if (nombre) this.renombrar.emit({ nombre, textoLegado: this.textoLegado() });
  }

  protected enviarMover(): void {
    const destino = this.destino();
    if (destino && this.destinoCambiado()) this.mover.emit(destino);
  }

  protected enviarNuevo(): void {
    if (!this.puedeCrear()) return;
    this.crear.emit({ tipo: this.tipoNuevo(), nombre: this.nombreNuevo().trim(), destino: this.tipoNuevo() === 'sector' ? null : this.destinoNuevo() });
  }

  /** The page calls this after a successful create */
  limpiarNuevo(): void {
    this.nombreNuevo.set('');
  }
}
