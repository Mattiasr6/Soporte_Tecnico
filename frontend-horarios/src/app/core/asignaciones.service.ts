import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Asignacion, Cesion, Reserva } from './modelos';

/** Filters for the asignaciones list */
export interface FiltroAsignaciones {
  /** Only those ending on or after this date (YYYY-MM-DD), e.g. today */
  finDesde?: string;
  /** Only those with a horario in this ambiente (and only those horarios) */
  ambienteId?: number;
}

/** Filters for the cesiones list */
export interface FiltroCesiones {
  lote?: string;
  excluirLote?: string | null;
  horarioIds?: number[];
}

/**
 * Reads and deletes of asignaciones, cesiones and reservas. Saving goes
 * through OcupacionService (it runs the clash-checked SQL RPCs).
 * Rows come with the same embeds the pages used: docente, materia, carrera,
 * horarios, fechas; receptor, horario.asignacion; tipo, reubicaciones.
 */
@Injectable({ providedIn: 'root' })
export class AsignacionesService {
  private readonly api = inject(ApiService);

  listar(filtro: FiltroAsignaciones = {}): Promise<Asignacion[]> {
    const params: Record<string, string | number | boolean> = {};
    if (filtro.finDesde) params['fin_desde'] = filtro.finDesde;
    if (filtro.ambienteId) params['ambiente_id'] = filtro.ambienteId;
    return this.api.get<Asignacion[]>('/asignaciones', params);
  }

  obtener(id: number): Promise<Asignacion> {
    return this.api.get<Asignacion>(`/asignaciones/${id}`);
  }

  eliminar(id: number): Promise<void> {
    return this.api.delete(`/asignaciones/${id}`);
  }

  /** Cesiones, newest first */
  listarCesiones(filtro: FiltroCesiones = {}): Promise<Cesion[]> {
    const query = new URLSearchParams();
    if (filtro.lote) query.set('lote', filtro.lote);
    if (filtro.excluirLote) query.set('excluir_lote', filtro.excluirLote);
    filtro.horarioIds?.forEach((id) => query.append('asignacion_horario_id', String(id)));
    const texto = query.toString();
    return this.api.get<Cesion[]>(`/cesiones${texto ? `?${texto}` : ''}`);
  }

  obtenerCesion(id: number): Promise<Cesion> {
    return this.api.get<Cesion>(`/cesiones/${id}`);
  }

  eliminarCesion(id: number): Promise<void> {
    return this.api.delete(`/cesiones/${id}`);
  }

  /** Reservas (eventos, defensas...), newest first */
  listarReservas(): Promise<Reserva[]> {
    return this.api.get<Reserva[]>('/reservas');
  }

  obtenerReserva(id: number): Promise<Reserva> {
    return this.api.get<Reserva>(`/reservas/${id}`);
  }

  eliminarReserva(id: number): Promise<void> {
    return this.api.delete(`/reservas/${id}`);
  }
}
