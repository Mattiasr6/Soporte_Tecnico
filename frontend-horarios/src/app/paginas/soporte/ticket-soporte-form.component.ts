import { Component, computed, input, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { normalizar } from '../../compartido/buscador.component';
import {
  ArbolJerarquia, AtencionSoporte, CambiosAtencionSoporte, CATEGORIAS_SOPORTE, MEDIOS_SOPORTE, SOLICITANTES_SOPORTE, UsuarioSoporte,
} from '../../core/soporte.service';

/** A pickable place: a dependencia (grupo) or an área, with its full path */
interface Destino {
  clave: string;
  ruta: string;
  busca: string;
  grupo_padre_id: number;
  grupo_id: number | null;
  area_id: number | null;
}

/**
 * Edición de una atención de Soporte (presentacional), con los mismos campos
 * que el ticket de Django: área (sector › dependencia › área), medio,
 * solicitante, categoría, textos, colaborador y fecha. Emite solo los campos
 * con valor, como el formulario de Django; la página hace la llamada.
 */
@Component({
  selector: 'app-ticket-soporte-form',
  imports: [FormsModule],
  template: `
    <form class="space-y-3" (ngSubmit)="enviar()">
      <div>
        <label class="etiqueta" for="ts-area">Área</label>
        @if (destino() && !eligiendo()) {
          <p class="flex flex-wrap items-center gap-2 text-sm">
            <span class="font-medium text-marca-700">{{ destino()!.ruta }}</span>
            <button class="btn-fantasma btn-sm" type="button" (click)="eligiendo.set(true)">Cambiar</button>
          </p>
        } @else {
          <input class="campo" id="ts-area" name="filtroArea" autocomplete="off" placeholder="Escribí para filtrar: sistemas, aula b, vicerrectorado…"
                 [ngModel]="filtroArea()" (ngModelChange)="filtroArea.set($event)">
          <ul class="mt-1 max-h-48 overflow-y-auto rounded-md border border-slate-200 text-sm" role="listbox" aria-label="Sector, dependencia y área">
            @for (d of destinosFiltrados(); track d.clave) {
              <li>
                <button type="button" class="w-full px-3 py-1.5 text-left hover:bg-slate-100" role="option"
                        [attr.aria-selected]="destino()?.clave === d.clave" (click)="elegir(d)">{{ d.ruta }}</button>
              </li>
            } @empty {
              <li class="px-3 py-1.5 text-slate-500">Sin coincidencias.</li>
            }
          </ul>
        }
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="ts-medio">Medio</label>
          <select class="campo" id="ts-medio" name="medio" [ngModel]="medio()" (ngModelChange)="medio.set($event)">
            @for (m of medios; track m) { <option [value]="m">{{ m }}</option> }
          </select>
        </div>
        <div>
          <label class="etiqueta" for="ts-solicitante">Solicitante</label>
          <select class="campo" id="ts-solicitante" name="solicitante" [ngModel]="solicitante()" (ngModelChange)="solicitante.set($event)">
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
      <div>
        <label class="etiqueta" for="ts-desc">Descripción</label>
        <textarea class="campo" id="ts-desc" name="descripcion" rows="3" required [ngModel]="descripcion()" (ngModelChange)="descripcion.set($event)"></textarea>
      </div>
      <div>
        <label class="etiqueta" for="ts-sol">Solución</label>
        <textarea class="campo" id="ts-sol" name="solucion" rows="3" required [ngModel]="solucion()" (ngModelChange)="solucion.set($event)"></textarea>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="ts-obs">Observaciones</label>
          <input class="campo" id="ts-obs" name="observaciones" [ngModel]="observaciones()" (ngModelChange)="observaciones.set($event)">
        </div>
        <div>
          <label class="etiqueta" for="ts-enl">Enlace de apoyo</label>
          <input class="campo" id="ts-enl" name="enlace" [ngModel]="enlace()" (ngModelChange)="enlace.set($event)">
        </div>
      </div>
      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="etiqueta" for="ts-col">Colaborador</label>
          <select class="campo" id="ts-col" name="colaborador" [ngModel]="colaborador()" (ngModelChange)="colaborador.set($event)">
            <option [ngValue]="null">— Sin colaborador —</option>
            @for (u of usuarios(); track u.id) { <option [ngValue]="u.id">{{ u.display_name }}</option> }
          </select>
        </div>
        <div>
          <label class="etiqueta" for="ts-fec">Fecha</label>
          <input class="campo" id="ts-fec" name="fecha" type="date" [ngModel]="fecha()" (ngModelChange)="fecha.set($event)">
        </div>
      </div>
      @if (error()) { <p class="text-sm text-red-700">{{ error() }}</p> }
      <footer class="flex gap-2 border-t border-slate-200 pt-3">
        <button class="btn-primario" type="submit" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Guardar cambios' }}</button>
        <button class="btn-secundario" type="button" (click)="cancelar.emit()">Cancelar</button>
      </footer>
    </form>
  `,
})
export class TicketSoporteFormComponent implements OnInit {
  readonly atencion = input.required<AtencionSoporte>();
  readonly arbol = input<ArbolJerarquia | null>(null);
  /** Possible collaborators (active Técnicos and Jefes) */
  readonly usuarios = input<UsuarioSoporte[]>([]);
  readonly guardando = input(false);
  readonly guardar = output<CambiosAtencionSoporte>();
  readonly cancelar = output<void>();

  protected readonly categorias = CATEGORIAS_SOPORTE;
  protected readonly medios = MEDIOS_SOPORTE;
  protected readonly solicitantes = SOLICITANTES_SOPORTE;

  protected readonly medio = signal('');
  protected readonly solicitante = signal('');
  protected readonly categoria = signal('');
  protected readonly descripcion = signal('');
  protected readonly solucion = signal('');
  protected readonly observaciones = signal('');
  protected readonly enlace = signal('');
  protected readonly colaborador = signal<number | null>(null);
  protected readonly fecha = signal('');
  protected readonly destino = signal<Destino | null>(null);
  protected readonly eligiendo = signal(false);
  protected readonly filtroArea = signal('');
  protected readonly error = signal('');

  /** Groups and areas as one flat list "Sector › Dependencia › Área" (like jerarquia.js) */
  protected readonly destinos = computed<Destino[]>(() => {
    const arbol = this.arbol();
    if (!arbol) return [];
    const salida: Destino[] = [];
    const agregar = (d: Omit<Destino, 'busca'>) => salida.push({ ...d, busca: normalizar(d.ruta) });
    for (const padre of arbol.padres) {
      for (const grupo of arbol.grupos.filter((g) => g.grupo_padre_id === padre.id)) {
        const rutaGrupo = `${padre.nombre} › ${grupo.nombre}`;
        agregar({ clave: `g${grupo.id}`, ruta: rutaGrupo, grupo_padre_id: padre.id, grupo_id: grupo.id, area_id: null });
        for (const area of arbol.areas.filter((a) => a.grupo_id === grupo.id)) {
          agregar({ clave: `a${area.id}`, ruta: `${rutaGrupo} › ${area.nombre}`, grupo_padre_id: padre.id, grupo_id: grupo.id, area_id: area.id });
        }
      }
      for (const area of arbol.areas.filter((a) => a.grupo_padre_id === padre.id && !a.grupo_id)) {
        agregar({ clave: `a${area.id}`, ruta: `${padre.nombre} › ${area.nombre}`, grupo_padre_id: padre.id, grupo_id: null, area_id: area.id });
      }
    }
    return salida;
  });

  protected readonly destinosFiltrados = computed(() => {
    const q = normalizar(this.filtroArea().trim());
    return q ? this.destinos().filter((d) => d.busca.includes(q)) : this.destinos();
  });

  ngOnInit(): void {
    const a = this.atencion();
    this.medio.set(a.medio_solicitud);
    this.solicitante.set(a.usuario_solicitante);
    this.categoria.set(a.categoria);
    this.descripcion.set(a.descripcion);
    this.solucion.set(a.solucion);
    this.observaciones.set(a.observaciones ?? '');
    this.enlace.set(a.enlace_apoyo ?? '');
    this.colaborador.set(a.colaborador_id);
    this.fecha.set(a.fecha_registro);
    const clave = a.area_id ? `a${a.area_id}` : a.grupo_id ? `g${a.grupo_id}` : '';
    this.destino.set(this.destinos().find((d) => d.clave === clave) ?? null);
    this.eligiendo.set(!this.destino());
  }

  protected elegir(d: Destino): void {
    this.destino.set(d);
    this.eligiendo.set(false);
    this.filtroArea.set('');
  }

  protected enviar(): void {
    const destino = this.destino();
    if (!destino && this.atencion().grupo_padre_id === null) {
      this.error.set('Elegí un área o dependencia de la lista.');
      return;
    }
    if (!this.categoria() || !this.descripcion().trim() || !this.solucion().trim()) {
      this.error.set('Completá la categoría, la descripción y la solución.');
      return;
    }
    this.error.set('');
    // Like Django `_cuerpo_edicion`: empty fields are left out (the backend keeps them)
    const cambios: CambiosAtencionSoporte = {};
    const textos = {
      medio_solicitud: this.medio(), usuario_solicitante: this.solicitante(), categoria: this.categoria(),
      descripcion: this.descripcion(), solucion: this.solucion(), observaciones: this.observaciones(),
      enlace_apoyo: this.enlace(), fecha_registro: this.fecha(),
    };
    for (const [campo, valor] of Object.entries(textos)) {
      if (valor) cambios[campo as keyof typeof textos] = valor;
    }
    if (destino) {
      cambios.grupo_padre_id = destino.grupo_padre_id;
      if (destino.grupo_id !== null) cambios.grupo_id = destino.grupo_id;
      if (destino.area_id !== null) cambios.area_id = destino.area_id;
    }
    const colaborador = this.colaborador();
    if (colaborador !== null) cambios.colaborador_id = colaborador;
    this.guardar.emit(cambios);
  }
}
