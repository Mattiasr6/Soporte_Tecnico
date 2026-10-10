import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** A chart series as the API builds it: one value per label */
export interface SerieSoporte {
  labels: string[];
  values: number[];
}

export type VistaReporte = 'mes' | 'anio';

/** GET /api/atenciones/reporte (Django `reportes_vista` payload) */
export interface ReporteSoporte {
  periodo: { vista: VistaReporte; mes: string; etiqueta: string; es_mes_en_curso: boolean };
  kpis: {
    total: number;
    prev_total: number | null;
    delta_abs: number | null;
    delta_pct: number | null;
    fuera_pct: number;
    fuera_delta_pts: number | null;
    promedio_dia: number;
    dias_periodo: number;
    areas_distintas: number;
    meses_activos: number;
  };
  charts: {
    evolucion: SerieSoporte;
    categoria: SerieSoporte;
    sectores: SerieSoporte;
    medio: SerieSoporte;
    tipo_solicitante: SerieSoporte;
    top_areas: { area: string; total: number; pct: number }[];
  };
  destacados: { id: number; area: string; categoria: string; descripcion: string; solucion: string }[];
  metodologia: { fuente: string; periodo: string; generado_en: string; corte: string };
}

/**
 * Soporte dashboard and report. The API computes every KPI and series (ported
 * from the Django views); it answers only to a Jefe or a user with
 * `CanViewDashboard`, anyone else gets 403.
 */
@Injectable({ providedIn: 'root' })
export class PanelSoporteService {
  private readonly api = inject(ApiRaizService);

  /** `mes` is "YYYY-MM"; the API falls back to the current month when it is invalid */
  reporte(mes: string, vista: VistaReporte): Promise<ReporteSoporte> {
    return this.api.get<ReporteSoporte>('/atenciones/reporte', { mes, vista });
  }
}
