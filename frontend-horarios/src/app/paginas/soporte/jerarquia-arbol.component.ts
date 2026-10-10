import { Component, computed, input, output } from '@angular/core';
import { ArbolJerarquiaCompleto, ConteosJerarquia, TipoNodo } from '../../core/jerarquia.service';

/** A tree node as the screen shows it, with its attention total */
export interface NodoJerarquia {
  tipo: TipoNodo;
  id: number;
  /** `<tipo>:<id>`, the Django `?nodo=` value */
  clave: string;
  nombre: string;
  codigo: string;
  /** Sectors are always active (the backend has no flag for them) */
  activo: boolean;
  total: number;
  grupo_padre_id: number;
  grupo_id: number | null;
}

export interface DependenciaRama extends NodoJerarquia {
  areas: NodoJerarquia[];
}

/** One sector with its dependencias and the áreas that hang directly from it */
export interface RamaJerarquia {
  sector: NodoJerarquia;
  grupos: DependenciaRama[];
  directas: NodoJerarquia[];
}

/** The selected node with its sector and, if any, its dependencia */
export interface DetalleJerarquia {
  nodo: NodoJerarquia;
  sector: NodoJerarquia;
  dependencia: NodoJerarquia | null;
}

/** Django `_armar_arbol`: tree plus per-node attention totals */
export function armarRamas(arbol: ArbolJerarquiaCompleto | null, conteos: ConteosJerarquia | null): RamaJerarquia[] {
  if (!arbol) return [];
  const total = (mapa: Map<number, number> | undefined, id: number) => mapa?.get(id) ?? 0;
  const areas: NodoJerarquia[] = arbol.areas.map((a) => ({
    tipo: 'area', id: a.id, clave: `area:${a.id}`, nombre: a.nombre, codigo: a.codigo, activo: a.activo,
    total: total(conteos?.areas, a.id), grupo_padre_id: a.grupo_padre_id, grupo_id: a.grupo_id,
  }));
  return arbol.padres.map((p) => ({
    sector: {
      tipo: 'sector', id: p.id, clave: `sector:${p.id}`, nombre: p.nombre, codigo: p.codigo, activo: true,
      total: total(conteos?.padres, p.id), grupo_padre_id: p.id, grupo_id: null,
    },
    grupos: arbol.grupos
      .filter((g) => g.grupo_padre_id === p.id)
      .map((g) => ({
        tipo: 'dependencia', id: g.id, clave: `dependencia:${g.id}`, nombre: g.nombre, codigo: g.codigo, activo: g.activo,
        total: total(conteos?.grupos, g.id), grupo_padre_id: p.id, grupo_id: g.id,
        areas: areas.filter((a) => a.grupo_id === g.id),
      })),
    directas: areas.filter((a) => a.grupo_padre_id === p.id && !a.grupo_id),
  }));
}

/** Django `_detalle`: finds the node of a `<tipo>:<id>` key */
export function detalleDe(ramas: RamaJerarquia[], clave: string | null): DetalleJerarquia | null {
  if (!clave) return null;
  for (const rama of ramas) {
    if (rama.sector.clave === clave) return { nodo: rama.sector, sector: rama.sector, dependencia: null };
    for (const grupo of rama.grupos) {
      if (grupo.clave === clave) return { nodo: grupo, sector: rama.sector, dependencia: grupo };
      const area = grupo.areas.find((a) => a.clave === clave);
      if (area) return { nodo: area, sector: rama.sector, dependencia: grupo };
    }
    const directa = rama.directas.find((a) => a.clave === clave);
    if (directa) return { nodo: directa, sector: rama.sector, dependencia: null };
  }
  return null;
}

/**
 * Árbol del catálogo (presentacional): sector › dependencia › área con el
 * total de atenciones de cada nodo, o solo las áreas sin dependencia.
 * Emite la clave del nodo elegido; la página decide qué hacer.
 */
@Component({
  selector: 'app-jerarquia-arbol',
  template: `
    <header class="mb-2 flex items-baseline justify-between gap-2">
      <h2 class="font-semibold">Catálogo</h2>
      <small class="text-xs text-slate-500">{{ sueltas().length }} área{{ sueltas().length === 1 ? '' : 's' }} sin dependencia</small>
    </header>

    @if (soloSueltas()) {
      <button type="button" class="mb-2 text-sm text-marca-700 hover:underline" (click)="verSueltas.emit(false)">← volver al árbol completo</button>
      <ul class="space-y-0.5 text-sm">
        @for (a of sueltas(); track a.nodo.clave) {
          <li>
            <button type="button" class="flex w-full items-center justify-between gap-2 rounded px-2 py-1 text-left hover:bg-slate-100"
                    [class.bg-marca-100]="seleccion() === a.nodo.clave" (click)="elegir.emit(a.nodo.clave)">
              <span>{{ a.sector }} › {{ a.nodo.nombre }}</span>
              <span class="chip bg-slate-100 text-slate-600">{{ a.nodo.total }}</span>
            </button>
          </li>
        } @empty {
          <li class="px-2 py-1 text-slate-500">No hay áreas sin dependencia.</li>
        }
      </ul>
    } @else {
      <button type="button" class="mb-2 text-sm text-marca-700 hover:underline" (click)="verSueltas.emit(true)">
        Ver solo las {{ sueltas().length }} áreas sin dependencia
      </button>
      <div class="space-y-1 text-sm">
        @for (rama of ramas(); track rama.sector.clave) {
          <details open class="rounded border border-slate-200">
            <summary class="flex cursor-pointer items-center gap-2 px-2 py-1.5">
              <button type="button" class="font-semibold hover:underline" [class.text-marca-700]="seleccion() === rama.sector.clave"
                      (click)="$event.preventDefault(); elegir.emit(rama.sector.clave)">{{ rama.sector.nombre }}</button>
              <span class="chip ml-auto bg-slate-100 text-slate-600">{{ rama.sector.total }}</span>
            </summary>
            <div class="space-y-0.5 pb-1 pl-4">
              @for (g of rama.grupos; track g.clave) {
                <details [open]="abierto() === g.clave">
                  <summary class="flex cursor-pointer items-center gap-2 px-2 py-1">
                    <button type="button" class="hover:underline" [class.text-marca-700]="seleccion() === g.clave"
                            (click)="$event.preventDefault(); elegir.emit(g.clave)">{{ g.nombre }}</button>
                    @if (!g.activo) { <span class="chip bg-slate-200 text-slate-500">inactiva</span> }
                    <span class="chip ml-auto bg-slate-100 text-slate-600">{{ g.total }}</span>
                  </summary>
                  <ul class="pl-4">
                    @for (a of g.areas; track a.clave) {
                      <li>
                        <button type="button" class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-slate-100"
                                [class.bg-marca-100]="seleccion() === a.clave" (click)="elegir.emit(a.clave)">
                          <span>{{ a.nombre }}</span>
                          @if (!a.activo) { <span class="chip bg-slate-200 text-slate-500">inactiva</span> }
                          <span class="chip ml-auto bg-slate-100 text-slate-600">{{ a.total }}</span>
                        </button>
                      </li>
                    }
                  </ul>
                </details>
              }
              @for (a of rama.directas; track a.clave) {
                <button type="button" class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-slate-100"
                        [class.bg-marca-100]="seleccion() === a.clave" (click)="elegir.emit(a.clave)">
                  <span>{{ a.nombre }}</span>
                  @if (!a.activo) { <span class="chip bg-slate-200 text-slate-500">inactiva</span> }
                  <span class="chip ml-auto bg-slate-100 text-slate-600">{{ a.total }}</span>
                </button>
              }
            </div>
          </details>
        }
      </div>
    }
  `,
})
export class JerarquiaArbolComponent {
  readonly ramas = input<RamaJerarquia[]>([]);
  /** Key of the selected node (`<tipo>:<id>`) */
  readonly seleccion = input<string | null>(null);
  /** Key of the dependencia to keep open (the selected node's one) */
  readonly abierto = input<string | null>(null);
  readonly soloSueltas = input(false);

  readonly elegir = output<string>();
  readonly verSueltas = output<boolean>();

  /** Áreas without a dependencia, with their sector name */
  protected readonly sueltas = computed(() =>
    this.ramas().flatMap((r) => r.directas.map((nodo) => ({ nodo, sector: r.sector.nombre }))),
  );
}
