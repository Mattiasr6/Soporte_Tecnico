import { Component, computed, input, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { normalizar } from '../../compartido/buscador.component';
import { ArbolJerarquia } from '../../core/soporte.service';

/** A pickable place: a dependencia (grupo) or an área, with its full path */
export interface DestinoSoporte {
  /** `g<id>` for a dependencia, `a<id>` for an área */
  clave: string;
  ruta: string;
  busca: string;
  grupo_padre_id: number;
  grupo_id: number | null;
  area_id: number | null;
}

/** Groups and areas as one flat list "Sector › Dependencia › Área" (like jerarquia.js) */
export function destinosDeArbol(arbol: ArbolJerarquia | null): DestinoSoporte[] {
  if (!arbol) return [];
  const salida: DestinoSoporte[] = [];
  const agregar = (d: Omit<DestinoSoporte, 'busca'>) => salida.push({ ...d, busca: normalizar(d.ruta) });
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
}

/** Key of the place an attention points to (área first, then dependencia) */
export function claveDestino(areaId: number | null | undefined, grupoId: number | null | undefined): string {
  return areaId ? `a${areaId}` : grupoId ? `g${grupoId}` : '';
}

/**
 * Selector de área de Soporte (presentacional): sector › dependencia › área
 * con filtro de texto. Muestra la ruta elegida con "Cambiar", o la lista
 * filtrable cuando todavía no hay nada elegido.
 */
@Component({
  selector: 'app-selector-area-soporte',
  imports: [FormsModule],
  template: `
    <label class="etiqueta" [for]="idCampo()">Área</label>
    @if (seleccion() && !eligiendo()) {
      <p class="flex flex-wrap items-center gap-2 text-sm">
        <span class="font-medium text-marca-700">{{ seleccion()!.ruta }}</span>
        <button class="btn-fantasma btn-sm" type="button" (click)="eligiendo.set(true)">Cambiar</button>
      </p>
    } @else {
      <input class="campo" [id]="idCampo()" name="filtroArea" autocomplete="off" placeholder="Escribí para filtrar: sistemas, aula b, vicerrectorado…"
             [ngModel]="filtro()" (ngModelChange)="filtro.set($event)">
      <ul class="mt-1 max-h-48 overflow-y-auto rounded-md border border-slate-200 text-sm" role="listbox" aria-label="Sector, dependencia y área">
        @for (d of filtrados(); track d.clave) {
          <li>
            <button type="button" class="w-full px-3 py-1.5 text-left hover:bg-slate-100" role="option"
                    [attr.aria-selected]="seleccion()?.clave === d.clave" (click)="elegir(d)">{{ d.ruta }}</button>
          </li>
        } @empty {
          <li class="px-3 py-1.5 text-slate-500">Sin coincidencias.</li>
        }
      </ul>
    }
  `,
})
export class SelectorAreaSoporteComponent {
  readonly destinos = input<DestinoSoporte[]>([]);
  readonly seleccion = model<DestinoSoporte | null>(null);
  readonly idCampo = input('sel-area');

  protected readonly eligiendo = signal(false);
  protected readonly filtro = signal('');

  protected readonly filtrados = computed(() => {
    const q = normalizar(this.filtro().trim());
    return q ? this.destinos().filter((d) => d.busca.includes(q)) : this.destinos();
  });

  protected elegir(d: DestinoSoporte): void {
    this.seleccion.set(d);
    this.eligiendo.set(false);
    this.filtro.set('');
  }
}
