import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** One Soporte attention as GET /api/atenciones returns it (AtencionOut) */
export interface AtencionSoporte {
  id: number;
  usuario_id: number;
  usuario_nombre: string;
  area_solicitante: string;
  grupo_padre_id: number | null;
  grupo_padre_nombre: string | null;
  grupo_id: number | null;
  grupo_nombre: string | null;
  area_id: number | null;
  area_nombre: string | null;
  medio_solicitud: string;
  usuario_solicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones: string | null;
  enlace_apoyo: string | null;
  colaborador_id: number | null;
  colaborador_nombre: string | null;
  /** ISO date (YYYY-MM-DD) */
  fecha_registro: string;
  fuera_de_turno: boolean;
  created_at: string;
}

/** Body of PUT /api/atenciones/{id}: only the fields that are sent change */
export interface CambiosAtencionSoporte {
  medio_solicitud?: string;
  usuario_solicitante?: string;
  categoria?: string;
  descripcion?: string;
  solucion?: string;
  observaciones?: string;
  enlace_apoyo?: string;
  fecha_registro?: string;
  grupo_padre_id?: number;
  grupo_id?: number;
  area_id?: number;
  colaborador_id?: number;
}

/** One row of POST /api/atenciones/batch (AtencionCreate), as Django `_item_nueva_desde_post` builds it */
export interface NuevaAtencionSoporte {
  /** Always empty: the backend derives the legacy name from the área or dependencia */
  area_solicitante: string;
  grupo_padre_id: number | null;
  grupo_id: number | null;
  area_id: number | null;
  medio_solicitud: string;
  usuario_solicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones: string | null;
  enlace_apoyo: string | null;
  colaborador_id: number | null;
  /** ISO date (YYYY-MM-DD) */
  fecha_registro: string;
}

/** GET /api/jerarquia/arbol: sector (padre) › dependencia (grupo) › área */
export interface ArbolJerarquia {
  padres: { id: number; nombre: string; orden: number }[];
  grupos: { id: number; grupo_padre_id: number; nombre: string }[];
  areas: { id: number; grupo_padre_id: number; grupo_id: number | null; nombre: string }[];
}

/** Soporte user (GET /api/usuarios), only the fields this area reads */
export interface UsuarioSoporte {
  id: number;
  display_name: string;
  role: string;
  activo: boolean;
}

/** Same lists as the Django screens (backend `CATEGORIAS_VALIDAS`) */
export const CATEGORIAS_SOPORTE = [
  'Audio/Video', 'Cuentas/Accesos', 'Hardware', 'Impresión', 'Otros', 'Redes/Conectividad', 'Sistemas académicos', 'Software',
] as const;
export const MEDIOS_SOPORTE = ['Interno', 'Presencial', 'WhatsApp', 'E-ticket'] as const;
export const SOLICITANTES_SOPORTE = ['ADM', 'BEC', 'DOC', 'EST'] as const;

/**
 * Soporte attentions (old Soporte table, not `horarios.atenciones`). The backend
 * decides visibility: Jefe or dashboard users see everyone's and may filter by
 * technician; the rest only see their own. Only the owner edits or deletes.
 */
@Injectable({ providedIn: 'root' })
export class SoporteService {
  private readonly api = inject(ApiRaizService);

  /** `usuarioId` only has effect for Jefe / dashboard users */
  listarAtenciones(usuarioId: number | null): Promise<AtencionSoporte[]> {
    return this.api.get<AtencionSoporte[]>('/atenciones', usuarioId ? { usuario_id: usuarioId } : undefined);
  }

  actualizarAtencion(id: number, cambios: CambiosAtencionSoporte): Promise<void> {
    return this.api.put<void>(`/atenciones/${id}`, cambios);
  }

  /** The 10 most recent attentions the user can see (Django "Atenciones recientes") */
  recientes(): Promise<AtencionSoporte[]> {
    return this.api.get<AtencionSoporte[]>('/atenciones', { limit: 10 });
  }

  /** All rows in one transaction: either every row is stored or none */
  registrarLote(atenciones: NuevaAtencionSoporte[]): Promise<{ registros_insertados: number }> {
    return this.api.post<{ registros_insertados: number }>('/atenciones/batch', { atenciones });
  }

  eliminarAtencion(id: number): Promise<void> {
    return this.api.delete(`/atenciones/${id}`);
  }

  arbol(): Promise<ArbolJerarquia> {
    return this.api.get<ArbolJerarquia>('/jerarquia/arbol');
  }

  /**
   * Without `incluirInactivos` the backend returns active Técnicos and Jefes.
   * The Wilmercito assistant account is hidden: Wilmercito does not exist in Angular.
   */
  async usuarios(incluirInactivos = false): Promise<UsuarioSoporte[]> {
    const usuarios = await this.api.get<UsuarioSoporte[]>(
      '/usuarios',
      incluirInactivos ? { incluir_inactivos: true } : undefined,
    );
    return usuarios.filter((u) => !/wilmercito/i.test(u.display_name));
  }
}
