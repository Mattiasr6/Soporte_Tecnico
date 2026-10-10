import { Component, computed, input } from '@angular/core';
import { BarrasRankingComponent, FilaRanking } from '../../compartido/barras-ranking.component';
import { GraficoDonaComponent } from '../../compartido/grafico-dona.component';
import { GraficoLineasComponent } from '../../compartido/grafico-lineas.component';
import { SerieGrafico } from '../../compartido/graficos';
import { ReporteSoporte, SerieSoporte } from '../../core/panel-soporte.service';

const SIN_DATOS = 'Sin atenciones registradas en este período';

/** Django `floatformat:1` with a decimal comma: 40 -> '40,0' */
export function unDecimal(v: number): string {
  return v.toFixed(1).replace('.', ',');
}

export function filasDeSerie(s: SerieSoporte): FilaRanking[] {
  return s.labels.map((etiqueta, i) => ({ etiqueta, valor: s.values[i] ?? 0 }));
}

/**
 * Monthly Soporte report (presentational), like Django `reportes.html`: five
 * KPIs with the change against the previous month, the year trend, categories,
 * sectors, request channel and requester type, top 10 areas and the featured
 * cases. Printable: the container prints only this block.
 */
@Component({
  selector: 'app-reportes-soporte-vista',
  imports: [BarrasRankingComponent, GraficoDonaComponent, GraficoLineasComponent],
  template: `
    @let r = reporte();
    @let k = r.kpis;
    <div class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-5">
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Total de atenciones</p>
        <p class="text-3xl font-bold tabular-nums">{{ k.total }}</p>
        @if (k.delta_pct !== null) {
          <p class="text-xs font-medium" [class]="k.delta_pct >= 0 ? 'text-emerald-700' : 'text-red-700'">
            {{ k.delta_pct >= 0 ? '▲' : '▼' }} {{ uno(k.delta_pct) }}% ({{ (k.delta_abs ?? 0) >= 0 ? '+' : '' }}{{ k.delta_abs }})
          </p>
        } @else if (k.prev_total === 0 && k.total === 0) {
          <p class="text-xs text-slate-500">— sin variación</p>
        } @else if (k.prev_total === 0) {
          <p class="text-xs text-slate-500">s/d (+{{ k.delta_abs }}) · mes previo sin registros</p>
        }
      </div>
      <div class="tarjeta p-3">
        @if (r.periodo.vista === 'anio') {
          <p class="text-xs text-slate-500">Meses con datos</p>
          <p class="text-3xl font-bold tabular-nums">{{ k.meses_activos }}</p>
        } @else {
          <p class="text-xs text-slate-500">Mes anterior</p>
          <p class="text-3xl font-bold tabular-nums">{{ k.prev_total }}</p>
        }
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Fuera de turno</p>
        <p class="text-3xl font-bold tabular-nums">{{ uno(k.fuera_pct) }}%</p>
        @if (k.fuera_delta_pts !== null) {
          <!-- more after-hours work is the bad direction -->
          <p class="text-xs font-medium" [class]="k.fuera_delta_pts >= 0 ? 'text-red-700' : 'text-emerald-700'">
            {{ k.fuera_delta_pts >= 0 ? '▲' : '▼' }} {{ uno(k.fuera_delta_pts) }} pts
          </p>
        }
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Promedio por día</p>
        <p class="text-3xl font-bold tabular-nums">{{ uno(k.promedio_dia) }}</p>
        <p class="text-xs text-slate-500">{{ k.dias_periodo }} días hábiles (lun–sáb)</p>
      </div>
      <div class="tarjeta p-3">
        <p class="text-xs text-slate-500">Áreas distintas</p>
        <p class="text-3xl font-bold tabular-nums">{{ k.areas_distintas }}</p>
      </div>
    </div>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Evolución {{ r.periodo.mes.slice(0, 4) }}</h2>
      <p class="mb-2 text-xs text-slate-500">atenciones por mes</p>
      <app-grafico-lineas [etiquetas]="r.charts.evolucion.labels" [series]="serieEvolucion()" [alto]="200" />
    </section>

    <div class="mb-5 grid gap-5 lg:grid-cols-2">
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Por categoría</h2>
        <p class="mb-2 text-xs text-slate-500">cómo se clasificó el trabajo</p>
        <app-barras-ranking [filas]="categorias()" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Dónde se concentró</h2>
        <p class="mb-2 text-xs text-slate-500">sectores solicitantes</p>
        <app-barras-ranking [filas]="sectores()" color="var(--serie-2)" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Cómo llegó</h2>
        <p class="mb-2 text-xs text-slate-500">medio de solicitud</p>
        <app-grafico-dona [etiquetas]="r.charts.medio.labels" [valores]="r.charts.medio.values" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Quién pidió</h2>
        <p class="mb-2 text-xs text-slate-500">tipo de solicitante</p>
        <app-grafico-dona [etiquetas]="r.charts.tipo_solicitante.labels" [valores]="r.charts.tipo_solicitante.values" [vacio]="sinDatos" />
      </section>
    </div>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Top 10 áreas solicitantes</h2>
      <p class="mb-2 text-xs text-slate-500">volumen y peso relativo</p>
      @if (r.charts.top_areas.length) {
        <div class="overflow-x-auto">
          <table class="tabla">
            <thead><tr><th>#</th><th>Área</th><th class="text-right">Atenciones</th><th class="text-right">% del período</th></tr></thead>
            <tbody>
              @for (f of r.charts.top_areas; track $index) {
                <tr><td>{{ $index + 1 }}</td><td>{{ f.area }}</td><td class="text-right tabular-nums">{{ f.total }}</td><td class="text-right tabular-nums">{{ uno(f.pct) }}%</td></tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
      }
    </section>

    @if (r.periodo.vista === 'mes') {
      <section class="tarjeta mb-5 p-4">
        <h2 class="font-semibold">Trabajo destacado</h2>
        <p class="mb-2 text-xs text-slate-500">casos del período y su solución</p>
        @for (c of r.destacados; track c.id) {
          <article class="border-t border-slate-100 py-3 first:border-t-0">
            <p class="flex flex-wrap gap-2 text-xs"><span class="chip bg-marca-50 text-marca-700">{{ c.categoria }}</span><b>{{ c.area }}</b></p>
            <p class="mt-1 text-sm">{{ c.descripcion }}</p>
            <p class="mt-1 text-sm text-slate-600"><span class="font-medium">Solución:</span> {{ c.solucion }}</p>
          </article>
        } @empty {
          <p class="py-6 text-center text-sm text-slate-500">Sin casos para destacar en este período</p>
        }
      </section>
    }

    <p class="text-xs text-slate-500">Período {{ r.metodologia.periodo }} · {{ r.metodologia.corte }}</p>
  `,
})
export class ReportesSoporteVistaComponent {
  readonly reporte = input.required<ReporteSoporte>();

  protected readonly sinDatos = SIN_DATOS;
  protected readonly uno = unDecimal;
  protected readonly serieEvolucion = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: 'var(--serie-1)', valores: this.reporte().charts.evolucion.values },
  ]);
  protected readonly categorias = computed(() => filasDeSerie(this.reporte().charts.categoria));
  protected readonly sectores = computed(() => filasDeSerie(this.reporte().charts.sectores));
}
