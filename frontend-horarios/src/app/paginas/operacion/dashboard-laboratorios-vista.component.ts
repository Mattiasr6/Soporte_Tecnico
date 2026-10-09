import { Component, computed, input } from '@angular/core';
import { GraficoBarrasComponent } from '../../compartido/grafico-barras.component';
import { GraficoLineasComponent } from '../../compartido/grafico-lineas.component';
import { SerieGrafico } from '../../compartido/graficos';
import { MedioSolicitud, TipoAtencion, TurnoCodigo } from '../../core/modelos';
import { TIPOS_TICKET, TURNOS_TICKET } from '../../core/tickets';

/** What horarios.fn_dashboard_laboratorios returns (GET /dashboard/laboratorios) */
export interface DashboardLaboratorios {
  kpis: {
    total: number;
    lab_top: { codigo: string; total: number } | null;
    turno_top: { turno: TurnoCodigo; total: number } | null;
    auxiliares_activos: number;
  };
  por_lab: { id: number; codigo: string; color: string | null; total: number; top_tipo: TipoAtencion; top_turno: TurnoCodigo }[];
  por_tipo: { tipo: TipoAtencion; total: number }[];
  por_turno: { turno: TurnoCodigo; total: number }[];
  por_medio: { medio: MedioSolicitud; total: number }[];
  por_mes: { mes: string; total: number }[];
}

const SERIE_1 = 'var(--serie-1)';
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
export const NOMBRE_TURNO: Record<TurnoCodigo, string> = Object.fromEntries(
  TURNOS_TICKET.map((t) => [t.valor, t.texto])) as Record<TurnoCodigo, string>;

export function nombreTipo(tipo: TipoAtencion | null | undefined): string {
  return tipo ? TIPOS_TICKET[tipo]?.texto ?? tipo : '—';
}

/**
 * Lab dashboard (presentational), like Django's `laboratorios_dashboard.html`:
 * KPIs of the period, a per-lab table with its main type and turno, the year
 * trend and the counts by lab, type, turno and request channel.
 */
@Component({
  selector: 'app-dashboard-laboratorios-vista',
  imports: [GraficoBarrasComponent, GraficoLineasComponent],
  template: `
    @let d = datos();
    <div class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Atenciones del período</p>
        <p class="text-3xl font-bold tabular-nums">{{ d.kpis.total }}</p>
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Laboratorio con más atenciones</p>
        <p class="text-2xl font-bold">{{ d.kpis.lab_top?.codigo ?? '—' }}</p>
        @if (d.kpis.lab_top; as l) { <p class="text-xs text-slate-500">{{ l.total }} atenciones</p> }
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Turno con más atenciones</p>
        <p class="text-2xl font-bold">{{ d.kpis.turno_top ? nombreTurno[d.kpis.turno_top.turno] : '—' }}</p>
        @if (d.kpis.turno_top; as t) { <p class="text-xs text-slate-500">{{ t.total }} atenciones</p> }
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Auxiliares activos</p>
        <p class="text-3xl font-bold tabular-nums">{{ d.kpis.auxiliares_activos }}</p>
        <p class="text-xs text-slate-500">registraron al menos una</p>
      </div>
    </div>

    <section class="tarjeta mb-5 p-4">
      <h2 class="mb-2 font-semibold">Por laboratorio</h2>
      @if (d.por_lab.length) {
        <div class="overflow-x-auto">
          <table class="tabla">
            <thead>
              <tr><th>Laboratorio</th><th class="text-right">Atenciones</th><th>Categoría principal</th><th>Turno principal</th></tr>
            </thead>
            <tbody>
              @for (l of d.por_lab; track l.id) {
                <tr>
                  <td class="font-medium">
                    <span class="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm" [style.background]="l.color || 'var(--serie-1)'"></span>{{ l.codigo }}
                  </td>
                  <td class="text-right tabular-nums">{{ l.total }}</td>
                  <td>{{ nombreTipo(l.top_tipo) }}</td>
                  <td>{{ nombreTurno[l.top_turno] ?? '—' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="py-6 text-center text-sm text-slate-500">No hay atenciones con esos filtros.</p>
      }
    </section>

    <section class="tarjeta mb-5 p-4">
      <h2 class="mb-2 font-semibold">Tendencia del año</h2>
      <app-grafico-lineas [etiquetas]="mesesAnio()" [titulos]="titulosAnio()" [series]="serieAnio()" [alto]="200" />
    </section>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Atenciones por laboratorio</h2>
        <app-grafico-barras [etiquetas]="labs()" [series]="serieLabs()" [alto]="190" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Atenciones por turno</h2>
        <app-grafico-barras [etiquetas]="turnos()" [series]="serieTurnos()" [alto]="190" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Atenciones por categoría</h2>
        <app-grafico-barras [etiquetas]="tiposCortos()" [titulos]="tipos()" [series]="serieTipos()" [alto]="190" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Medio de solicitud</h2>
        @if (d.por_medio.length) {
          <ul class="space-y-2 text-sm">
            @for (m of d.por_medio; track m.medio) {
              <li>
                <div class="flex justify-between"><span>{{ m.medio }}</span><b class="tabular-nums">{{ m.total }}</b></div>
                <div class="mt-1 h-2 rounded bg-slate-100">
                  <div class="h-2 rounded" [style.width.%]="d.kpis.total ? (m.total * 100) / d.kpis.total : 0" style="background: var(--serie-1)"></div>
                </div>
              </li>
            }
          </ul>
        } @else {
          <p class="py-6 text-center text-sm text-slate-500">Sin datos.</p>
        }
      </section>
    </div>
  `,
})
export class DashboardLaboratoriosVistaComponent {
  readonly datos = input.required<DashboardLaboratorios>();

  protected readonly nombreTurno = NOMBRE_TURNO;
  protected readonly nombreTipo = nombreTipo;

  protected readonly mesesAnio = computed(() => this.datos().por_mes.map((m) => MESES[Number(m.mes.slice(5, 7)) - 1]));
  protected readonly titulosAnio = computed(() => this.datos().por_mes.map((m) => `${MESES[Number(m.mes.slice(5, 7)) - 1]} ${m.mes.slice(0, 4)}`));
  protected readonly serieAnio = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: SERIE_1, valores: this.datos().por_mes.map((m) => m.total) },
  ]);
  protected readonly labs = computed(() => this.datos().por_lab.map((l) => l.codigo));
  protected readonly serieLabs = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: SERIE_1, valores: this.datos().por_lab.map((l) => l.total) },
  ]);
  protected readonly turnos = computed(() => this.datos().por_turno.map((t) => NOMBRE_TURNO[t.turno]));
  protected readonly serieTurnos = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: SERIE_1, valores: this.datos().por_turno.map((t) => t.total) },
  ]);
  protected readonly tipos = computed(() => this.datos().por_tipo.map((t) => nombreTipo(t.tipo)));
  protected readonly tiposCortos = computed(() => this.datos().por_tipo.map((t) => TIPOS_TICKET[t.tipo]?.corto ?? t.tipo));
  protected readonly serieTipos = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: SERIE_1, valores: this.datos().por_tipo.map((t) => t.total) },
  ]);
}
