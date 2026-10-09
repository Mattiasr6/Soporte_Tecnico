import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  Ambiente, Asignacion, CandidatoChoque, Choque, Conflicto, EstadoVivoAmbiente, IgnorarChoque, Ocupacion, Reserva,
} from './modelos';

/** Payload with an optional id: present = update, absent/null = create */
type ConId = { id?: number | null };

/**
 * Ocupación, choques y guardado (endpoints `/api/asignacion/...` que envuelven
 * las funciones SQL fn_* y rpc_* de Postgres).
 */
@Injectable({ providedIn: 'root' })
export class OcupacionService {
  private readonly api = inject(ApiService);

  /** Todo lo que ocupa ambientes entre dos fechas (clases, cesiones, reservas) */
  ocupaciones(desde: string, hasta: string): Promise<Ocupacion[]> {
    return this.api.get<Ocupacion[]>('/ocupaciones', { desde, hasta });
  }

  /** Choques existentes en un rango */
  conflictos(desde: string, hasta: string): Promise<Conflicto[]> {
    return this.api.get<Conflicto[]>('/conflictos', { desde, hasta });
  }

  /** Verifica candidatos antes de guardar (validación en vivo) */
  async verificarChoques(items: CandidatoChoque[], ignorar: IgnorarChoque = {}): Promise<Choque[]> {
    if (!items.length) return [];
    return this.api.post<Choque[]>('/choques/verificar', { items, ignorar });
  }

  /** Ambientes libres en una fecha y rango de horas */
  ambientesLibres(fecha: string, horaInicio: string, horaFin: string, ignorar: IgnorarChoque = {}, tipo: string | null = null): Promise<Ambiente[]> {
    return this.api.post<Ambiente[]>('/ambientes-libres', {
      fecha, hora_inicio: horaInicio, hora_fin: horaFin, tipo, ignorar,
    });
  }

  /** Ambientes libres en TODAS las fechas dadas (ej. todos los martes marcados) */
  async ambientesLibresFechas(fechas: string[], horaInicio: string, horaFin: string,
    ignorar: IgnorarChoque = {}, tipo: string | null = null): Promise<Ambiente[]> {
    if (!fechas.length) return [];
    return this.api.post<Ambiente[]>('/ambientes-libres/fechas', {
      fechas, hora_inicio: horaInicio, hora_fin: horaFin, tipo, ignorar,
    });
  }

  /** Estado libre/ocupado de cada ambiente en este momento */
  estadoAmbientes(): Promise<EstadoVivoAmbiente[]> {
    return this.api.get<EstadoVivoAmbiente[]>('/estado-ambientes');
  }

  /** Guarda una asignación completa con sus horarios */
  async guardarAsignacion(datos: object): Promise<number> {
    const id = (datos as ConId).id;
    const guardada = id
      ? await this.api.put<Asignacion>(`/asignaciones/${id}`, datos)
      : await this.api.post<Asignacion>('/asignaciones', datos);
    return guardada.id;
  }

  /** Guarda un lote de cesiones (uno o varios horarios, cada uno con sus fechas) */
  async guardarCesiones(datos: object): Promise<string> {
    const lote = (datos as { lote?: string | null }).lote;
    const r = lote
      ? await this.api.put<{ lote: string }>(`/cesiones/lotes/${lote}`, datos)
      : await this.api.post<{ lote: string }>('/cesiones/lotes', datos);
    return r.lote;
  }

  /** Guarda un evento/defensa con sus horarios y reubicaciones obligatorias */
  async guardarReserva(datos: object): Promise<number> {
    const id = (datos as ConId).id;
    const guardada = id
      ? await this.api.put<Reserva>(`/reservas/${id}`, datos)
      : await this.api.post<Reserva>('/reservas', datos);
    return guardada.id;
  }

  /** Mueve o suspende una clase en una fecha concreta */
  async reubicarClase(datos: object): Promise<number> {
    return (await this.api.post<{ id: number }>('/reubicaciones', datos)).id;
  }

  /** Quita una reubicación: la clase vuelve a su ambiente original ese día */
  eliminarReubicacion(id: number): Promise<void> {
    return this.api.delete(`/reubicaciones/${id}`);
  }
}
