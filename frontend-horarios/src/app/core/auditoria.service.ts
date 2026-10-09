import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** One row of GET /api/auditoria (change trail of essential records) */
export interface CambioAuditoria {
  id: number;
  fecha: string;
  usuario_email: string | null;
  usuario_nombre: string | null;
  rol: string | null;
  accion: string;
  entidad: string;
  entidad_id: number | null;
  detalle: string | null;
}

/** Filters the backend accepts; empty values mean "all" */
export interface FiltroAuditoria {
  entidad: string;
  accion: string;
}

/** Entities the backend records (same list as the Django screen) */
export const ENTIDADES_AUDITORIA = ['laboratorio', 'software', 'software_lab', 'pcs_lab', 'atencion', 'atencion_lab', 'categoria'] as const;
export const ACCIONES_AUDITORIA = ['crear', 'editar', 'eliminar'] as const;
/** Rows the Django screen asks for by default */
export const LIMITE_AUDITORIA = 200;

/**
 * Read-only audit trail. The backend only answers to a Jefe or a user with
 * dashboard access (`is_privileged`); anyone else gets 403.
 */
@Injectable({ providedIn: 'root' })
export class AuditoriaService {
  private readonly api = inject(ApiRaizService);

  listar(filtro: FiltroAuditoria, limite = LIMITE_AUDITORIA): Promise<CambioAuditoria[]> {
    const params: Record<string, string | number> = { limite };
    if (filtro.entidad) params['entidad'] = filtro.entidad;
    if (filtro.accion) params['accion'] = filtro.accion;
    return this.api.get<CambioAuditoria[]>('/auditoria', params);
  }
}
