import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** One stored shift of a Técnico or Jefe for one weekday of a month (HorarioOut) */
export interface HorarioTecnico {
  id: number;
  usuario_id: number;
  nombre: string;
  label: string;
  /** 1 = lunes … 7 = domingo */
  dia_semana: number;
  hora_inicio1: string | null;
  hora_fin1: string | null;
  hora_inicio2: string | null;
  hora_fin2: string | null;
  mes: number;
  anio: number;
}

/** One row of POST /api/horarios/lote (AsignarIn); the label is derived by the API */
export interface AsignacionHorario {
  usuario_id: number;
  dia_semana: number;
  mes: number;
  anio: number;
  hora_inicio1: string | null;
  hora_fin1: string | null;
  hora_inicio2: string | null;
  hora_fin2: string | null;
}

/** A fixed block of the day and the Técnicos that cover it (CoberturaFranja) */
export interface FranjaCobertura {
  franja: string;
  hora: string;
  tecnicos: string[];
}

/** GET /api/horarios/cobertura: Monday stands for lunes–viernes, plus Saturday */
export interface CoberturaHorarios {
  mes: number;
  anio: number;
  laborable: FranjaCobertura[];
  sabado: FranjaCobertura[];
}

/**
 * Monthly shifts of the Soporte Técnicos and Jefes (`/api/horarios`), not the
 * auxiliares' horarios-turno. Reads: everyone (non-privileged users only get
 * their own rows); writes: Jefe or dashboard flag (backend `is_privileged`).
 */
@Injectable({ providedIn: 'root' })
export class HorariosTecnicosService {
  private readonly api = inject(ApiRaizService);

  listar(mes: number, anio: number): Promise<HorarioTecnico[]> {
    return this.api.get<HorarioTecnico[]>('/horarios', { mes, anio });
  }

  cobertura(mes: number, anio: number): Promise<CoberturaHorarios> {
    return this.api.get<CoberturaHorarios>('/horarios/cobertura', { mes, anio });
  }

  /** Upsert by (usuario, mes, año, día); the API rejects an empty list */
  guardarLote(asignaciones: AsignacionHorario[]): Promise<void> {
    return this.api.post<void>('/horarios/lote', { asignaciones });
  }

  /** Removes the shift of one person for one weekday of the month (no-op if none) */
  borrarDia(usuarioId: number, mes: number, anio: number, diaSemana: number): Promise<void> {
    const q = new URLSearchParams({ usuario_id: String(usuarioId), mes: String(mes), anio: String(anio), dia_semana: String(diaSemana) });
    return this.api.delete(`/horarios?${q.toString()}`);
  }
}
