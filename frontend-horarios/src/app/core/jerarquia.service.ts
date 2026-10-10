import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** Sector (GrupoPadreOut). Sectors have no `activo` flag in the backend */
export interface SectorJerarquia {
  id: number;
  nombre: string;
  codigo: string;
  descripcion: string | null;
  orden: number;
}

/** Dependencia (GrupoOut) */
export interface DependenciaJerarquia {
  id: number;
  grupo_padre_id: number;
  nombre: string;
  codigo: string;
  activo: boolean;
}

/** Área (AreaOut); `grupo_id` null means the área hangs directly from the sector */
export interface AreaJerarquia {
  id: number;
  grupo_padre_id: number;
  grupo_id: number | null;
  nombre: string;
  codigo: string;
  activo: boolean;
}

/** GET /api/jerarquia/arbol with every field (ArbolOut) */
export interface ArbolJerarquiaCompleto {
  padres: SectorJerarquia[];
  grupos: DependenciaJerarquia[];
  areas: AreaJerarquia[];
}

/** Attention totals per node id, from GET /api/atenciones/stats */
export interface ConteosJerarquia {
  padres: Map<number, number>;
  grupos: Map<number, number>;
  areas: Map<number, number>;
}

/** Node kind; the same words Django uses in `?nodo=<tipo>:<id>` */
export type TipoNodo = 'sector' | 'dependencia' | 'area';

/** Where a node goes: a sector, optionally inside one of its dependencias */
export interface UbicacionJerarquia {
  grupo_padre_id: number;
  grupo_id: number | null;
}

/** POST /api/jerarquia/areas/{id}/convertir-dependencia (AreaConversionOut) */
export interface ConversionArea {
  grupo_id: number;
  atenciones_movidas: number;
  area_eliminada: boolean;
}

/** API path of each node kind (Django `PASOS_JERARQUIA`) */
const RUTAS: Record<TipoNodo, string> = {
  sector: '/jerarquia/grupos-padres',
  dependencia: '/jerarquia/grupos',
  area: '/jerarquia/areas',
};

interface NodoConteo {
  id: number;
  total: number;
}

/**
 * Catalog of sectores › dependencias › áreas (Django `jerarquia_vista` and
 * `jerarquia_accion_vista`). Every write is Jefe or dashboard flag only
 * (backend `is_privileged`); the backend rejects a delete with children or
 * attentions and re-points attentions when a node moves.
 */
@Injectable({ providedIn: 'root' })
export class JerarquiaService {
  private readonly api = inject(ApiRaizService);

  /** The whole tree, inactive nodes included (Django passes `incluir_inactivas=true`) */
  arbol(): Promise<ArbolJerarquiaCompleto> {
    return this.api.get<ArbolJerarquiaCompleto>('/jerarquia/arbol', { incluir_inactivas: true });
  }

  /** Attention totals per sector, dependencia and área (all time, like Django) */
  async conteos(): Promise<ConteosJerarquia> {
    const stats = await this.api.get<{ por_padre: NodoConteo[]; por_grupo: NodoConteo[]; por_area_id: NodoConteo[] }>('/atenciones/stats');
    const mapa = (lista: NodoConteo[] | undefined) => new Map((lista ?? []).map((c) => [c.id, c.total]));
    return { padres: mapa(stats.por_padre), grupos: mapa(stats.por_grupo), areas: mapa(stats.por_area_id) };
  }

  /** Sector: only the name. Dependencia: sector. Área: sector and optional dependencia */
  crear(tipo: TipoNodo, nombre: string, ubicacion: UbicacionJerarquia | null): Promise<unknown> {
    const cuerpo: Record<string, unknown> = { nombre };
    if (tipo !== 'sector' && ubicacion) {
      cuerpo['grupo_padre_id'] = ubicacion.grupo_padre_id;
      if (tipo === 'area') cuerpo['grupo_id'] = ubicacion.grupo_id;
    }
    return this.api.post(RUTAS[tipo], cuerpo);
  }

  /** The code never changes; for an área the attentions' legacy text can follow the new name */
  renombrar(tipo: TipoNodo, id: number, nombre: string, actualizarTextoLegado = false): Promise<unknown> {
    const cuerpo: Record<string, unknown> = { nombre };
    if (tipo === 'area') cuerpo['actualizar_texto_legado'] = actualizarTextoLegado;
    return this.api.put(`${RUTAS[tipo]}/${id}`, cuerpo);
  }

  /** A dependencia moves to another sector; an área to a sector or a dependencia */
  mover(tipo: 'dependencia' | 'area', id: number, ubicacion: UbicacionJerarquia): Promise<unknown> {
    const cuerpo = tipo === 'area' ? { grupo_padre_id: ubicacion.grupo_padre_id, grupo_id: ubicacion.grupo_id } : { grupo_padre_id: ubicacion.grupo_padre_id };
    return this.api.put(`${RUTAS[tipo]}/${id}`, cuerpo);
  }

  fijarActivo(tipo: 'dependencia' | 'area', id: number, activo: boolean): Promise<unknown> {
    return this.api.put(`${RUTAS[tipo]}/${id}`, { activo });
  }

  borrar(tipo: TipoNodo, id: number): Promise<void> {
    return this.api.delete(`${RUTAS[tipo]}/${id}`);
  }

  convertirEnDependencia(areaId: number): Promise<ConversionArea> {
    return this.api.post<ConversionArea>(`${RUTAS.area}/${areaId}/convertir-dependencia`, {});
  }
}
