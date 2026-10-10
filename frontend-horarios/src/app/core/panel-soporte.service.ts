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

/** A node of the hierarchy counts (sector, dependency or area) */
export interface NodoConteoSoporte {
  id: number;
  nombre: string;
  total: number;
  padre_id: number | null;
  grupo_id: number | null;
}

/** GET /api/atenciones/dashboard (Django `_payload`: `_graficos` + `_ficha`) */
export interface DashboardSoporte {
  charts: {
    total: number;
    fuera_de_turno: number;
    arbol_conteos: { padres: NodoConteoSoporte[]; grupos: NodoConteoSoporte[]; areas: NodoConteoSoporte[] };
    calendario: { inicio: string | null; fin: string | null; datos: [string, number][]; max: number };
    sankey: { nodos: { name: string }[]; links: { source: string; target: string; value: number }[] };
    /** [casos, fuera de turno, nombre, % fuera] per technician */
    scatter: { datos: [number, number, string, number][] };
    radar: { ejes: string[]; tecnicos: { id: number; nombre: string; valores: number[]; total: number }[] };
    categoria: SerieSoporte;
    categoria_mes: { categorias: string[]; meses: string[]; celdas: [number, number, number][]; max: number };
    rendimiento: SerieSoporte;
    colaboraciones: SerieSoporte;
    evolucion: SerieSoporte;
    medio: SerieSoporte;
    tipo_solicitante: SerieSoporte;
    top_areas: { area: string; total: number }[];
  };
  ficha: {
    casos: number;
    nombre_padre: string | null;
    fuera: number;
    fuera_pct: number;
    promedio_mes: number;
    meses_activos: number;
    pico: string | null;
    pico_total: number;
    valle: string | null;
    valle_total: number;
    dominante: string | null;
    dominante_pct: number;
    top3_pct: number;
    pct_padre: number | null;
    delta_padre: number | null;
  };
}

/** Dashboard filters: month range ("YYYY-MM", empty = open) and the drill-down ids */
export interface FiltroDashboardSoporte {
  desde: string;
  hasta: string;
  grupo_padre_id: number | null;
  grupo_id: number | null;
  area_id: number | null;
}

/**
 * Soporte dashboard and report. The API computes every KPI and series (ported
 * from the Django views); it answers only to a Jefe or a user with
 * `CanViewDashboard`, anyone else gets 403.
 */
@Injectable({ providedIn: 'root' })
export class PanelSoporteService {
  private readonly api = inject(ApiRaizService);

  dashboard(f: FiltroDashboardSoporte): Promise<DashboardSoporte> {
    const params: Record<string, string | number> = {};
    if (f.desde) params['desde'] = f.desde;
    if (f.hasta) params['hasta'] = f.hasta;
    if (f.grupo_padre_id != null) params['grupo_padre_id'] = f.grupo_padre_id;
    if (f.grupo_id != null) params['grupo_id'] = f.grupo_id;
    if (f.area_id != null) params['area_id'] = f.area_id;
    return this.api.get<DashboardSoporte>('/atenciones/dashboard', params);
  }

  /** `mes` is "YYYY-MM"; the API falls back to the current month when it is invalid */
  reporte(mes: string, vista: VistaReporte): Promise<ReporteSoporte> {
    return this.api.get<ReporteSoporte>('/atenciones/reporte', { mes, vista });
  }
}
