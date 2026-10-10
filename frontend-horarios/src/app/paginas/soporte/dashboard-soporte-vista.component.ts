import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BarrasRankingComponent, FilaRanking } from '../../compartido/barras-ranking.component';
import { GraficoDispersionComponent, PuntoDispersion } from '../../compartido/grafico-dispersion.component';
import { GraficoDonaComponent } from '../../compartido/grafico-dona.component';
import { GraficoLineasComponent } from '../../compartido/grafico-lineas.component';
import { GraficoRadarComponent } from '../../compartido/grafico-radar.component';
import { SerieGrafico } from '../../compartido/graficos';
import { CeldaCalor, MapaCalorComponent } from '../../compartido/mapa-calor.component';
import { DashboardSoporte } from '../../core/panel-soporte.service';
import { filasDeSerie } from './reportes-soporte-vista.component';

/** A selected node of the drill-down */
export interface NodoElegido {
  id: number;
  nombre: string;
}

/** Drill-down state: sector › dependency › area (each optional, in that order) */
export interface AlcanceDashboard {
  padre: NodoElegido | null;
  grupo: NodoElegido | null;
  area: NodoElegido | null;
}

export type NivelAlcance = 'padre' | 'grupo' | 'area';

const SIN_DATOS = 'Sin datos para este filtro';
const DIAS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const DIA_MS = 86_400_000;

/** Django `num()`: Spanish thousands separator and decimal comma */
function num(v: number): string {
  return Number(v).toLocaleString('es');
}

/** "YYYY-MM-DD" as a UTC date (no timezone shift) */
function fechaUtc(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

/**
 * Soporte dashboard (presentational), like Django `dashboard.html`: the
 * hierarchy drill-down (click a bar to filter; the whole board reloads), the
 * filter summary, cases per day, the work flow, channel / requester / top
 * areas, load vs after-hours per technician, the technician profile,
 * categories, category × month, performance, collaborations and the monthly
 * trend. Selections are reported to the container, which owns the filters.
 */
@Component({
  selector: 'app-dashboard-soporte-vista',
  imports: [
    FormsModule, BarrasRankingComponent, GraficoDispersionComponent, GraficoDonaComponent, GraficoLineasComponent,
    GraficoRadarComponent, MapaCalorComponent,
  ],
  template: `
    @let c = datos().charts;
    <div class="mb-4 flex flex-wrap items-center gap-2 text-xs">
      @for (ch of chips(); track ch.nivel) {
        <span class="chip bg-marca-50 text-marca-700">{{ ch.nombre }}
          <button type="button" class="ml-1 font-bold" (click)="quitar.emit(ch.nivel)" [attr.aria-label]="'Quitar ' + ch.nombre">×</button></span>
      } @empty {
        <span class="chip bg-slate-100 text-slate-600">Sin filtro: se muestra todo el período</span>
      }
      @if (chips().length) { <button type="button" class="text-marca-600 hover:underline" (click)="limpiar.emit()">Limpiar todo</button> }
    </div>

    <div class="mb-5 grid gap-5 lg:grid-cols-2">
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Filtro jerárquico</h2>
        <p class="mb-2 text-xs text-slate-500">{{ nivelTexto() }}</p>
        <app-barras-ranking [filas]="drill()" [seleccionable]="true" (elegir)="elegir.emit($event)" vacio="Sin divisiones para este filtro" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Resumen del filtro</h2>
        <p class="mb-2 text-xs text-slate-500">{{ ruta() || 'Todo el período' }}</p>
        <dl class="divide-y divide-slate-100 text-sm">
          @for (f of ficha(); track f[0]) {
            <div class="flex justify-between gap-3 py-1.5"><dt class="text-slate-600">{{ f[0] }}</dt><dd class="text-right font-semibold tabular-nums">{{ f[1] }}</dd></div>
          }
        </dl>
      </section>
    </div>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Casos por día</h2>
      <p class="mb-2 text-xs text-slate-500">densidad diaria, estilo calendario</p>
      @if (calendario(); as cal) {
        <app-mapa-calor [filas]="dias" [columnas]="cal.columnas" [valores]="cal.valores" [titulos]="cal.titulos" [tamano]="13" />
      } @else {
        <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
      }
    </section>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Flujo del trabajo</h2>
      <p class="mb-2 text-xs text-slate-500">de dónde llega y cómo se clasifica</p>
      <div class="grid gap-5 lg:grid-cols-2">
        <div>
          <h3 class="mb-1 text-xs font-medium text-slate-500">Canal → categoría</h3>
          <app-barras-ranking [filas]="flujo().entrada" [vacio]="sinDatos" />
        </div>
        <div>
          <h3 class="mb-1 text-xs font-medium text-slate-500">Categoría → sector</h3>
          <app-barras-ranking [filas]="flujo().salida" color="var(--serie-3)" [vacio]="sinDatos" />
        </div>
      </div>
    </section>

    <div class="mb-5 grid gap-5 lg:grid-cols-3">
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Canal de contacto</h2>
        <p class="mb-2 text-xs text-slate-500">por dónde piden</p>
        <app-grafico-dona [etiquetas]="c.medio.labels" [valores]="c.medio.values" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Tipo de solicitante</h2>
        <p class="mb-2 text-xs text-slate-500">quién pide</p>
        <app-grafico-dona [etiquetas]="c.tipo_solicitante.labels" [valores]="c.tipo_solicitante.values" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Top 10 áreas solicitantes</h2>
        <p class="mb-2 text-xs text-slate-500">qué área pide</p>
        <app-barras-ranking [filas]="topAreas()" [vacio]="sinDatos" />
      </section>
    </div>

    <div class="mb-5 grid gap-5 lg:grid-cols-2">
      <section class="tarjeta p-4">
        <h2 class="font-semibold">Carga vs fuera de turno</h2>
        <p class="mb-2 text-xs text-slate-500">cada punto es un técnico</p>
        @if (puntos().length) {
          <app-grafico-dispersion [puntos]="puntos()" ejeX="casos" ejeY="fuera de turno" />
        } @else {
          <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
        }
      </section>
      <section class="tarjeta p-4">
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 class="font-semibold">Perfil por técnico</h2>
          @if (c.radar.tecnicos.length) {
            <select class="campo !w-48 !py-1 !text-xs" aria-label="Técnico" [ngModel]="perfil()?.id" (ngModelChange)="tecnicoId.set($event)">
              @for (t of c.radar.tecnicos; track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }
            </select>
          }
        </div>
        @if (perfil(); as p) {
          <app-grafico-radar [ejes]="c.radar.ejes" [valores]="p.valores" [max]="maxRadar()" />
        } @else {
          <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
        }
      </section>
    </div>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Casos por categoría</h2>
      <p class="mb-2 text-xs text-slate-500">según el filtro elegido</p>
      <app-barras-ranking [filas]="categorias()" [vacio]="sinDatos" />
    </section>

    <section class="tarjeta mb-5 p-4">
      <h2 class="font-semibold">Densidad por categoría y mes</h2>
      <p class="mb-2 text-xs text-slate-500">meses con más casos</p>
      @if (c.categoria_mes.celdas.length) {
        <app-mapa-calor [filas]="c.categoria_mes.categorias" [columnas]="c.categoria_mes.meses" [valores]="categoriaMes()" [numeros]="true" [tamano]="24" />
      } @else {
        <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
      }
    </section>

    <div class="mb-5 grid gap-5 lg:grid-cols-2">
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Rendimiento por técnico</h2>
        <app-barras-ranking [filas]="rendimiento()" color="var(--serie-1)" [vacio]="sinDatos" />
      </section>
      <section class="tarjeta p-4">
        <h2 class="mb-2 font-semibold">Colaboraciones</h2>
        <app-barras-ranking [filas]="colaboraciones()" color="var(--serie-2)" [vacio]="sinDatos" />
      </section>
    </div>

    <section class="tarjeta p-4">
      <h2 class="mb-2 font-semibold">Evolución mensual</h2>
      @if (c.evolucion.labels.length) {
        <app-grafico-lineas [etiquetas]="c.evolucion.labels" [series]="serieEvolucion()" [alto]="220" />
      } @else {
        <p class="py-6 text-center text-sm text-slate-500">{{ sinDatos }}</p>
      }
    </section>
  `,
})
export class DashboardSoporteVistaComponent {
  readonly datos = input.required<DashboardSoporte>();
  readonly alcance = input.required<AlcanceDashboard>();
  /** A bar of the drill-down was clicked; its id is 'p<id>', 'g<id>' or 'a<id>' */
  readonly elegir = output<FilaRanking>();
  readonly quitar = output<NivelAlcance>();
  readonly limpiar = output<void>();

  protected readonly sinDatos = SIN_DATOS;
  protected readonly dias = DIAS;
  /** Technician picked in the profile selector (null = the first one) */
  protected readonly tecnicoId = signal<number | null>(null);

  protected readonly chips = computed(() => {
    const a = this.alcance();
    return ([['padre', a.padre], ['grupo', a.grupo], ['area', a.area]] as const)
      .filter(([, n]) => n !== null)
      .map(([nivel, n]) => ({ nivel: nivel as NivelAlcance, nombre: n!.nombre }));
  });

  protected readonly ruta = computed(() => this.chips().map((c) => c.nombre).join(' › '));

  protected readonly nivelTexto = computed(() => {
    const a = this.alcance();
    if (!a.padre) return 'Nivel: Grupo Padre — clic para entrar';
    if (!a.grupo) return `Nivel: ${a.padre.nombre} — clic en un grupo`;
    return `Nivel: ${a.padre.nombre} › ${a.grupo.nombre}`;
  });

  /** Bars of the current drill level (Django `pintarDrill`) */
  protected readonly drill = computed<FilaRanking[]>(() => {
    const { padres, grupos, areas } = this.datos().charts.arbol_conteos;
    const a = this.alcance();
    let filas: FilaRanking[];
    if (!a.padre) {
      filas = padres.map((p) => ({ id: `p${p.id}`, etiqueta: p.nombre, valor: p.total }));
    } else if (!a.grupo) {
      const pid = a.padre.id;
      filas = [
        ...grupos.filter((g) => g.padre_id === pid).map((g) => ({ id: `g${g.id}`, etiqueta: g.nombre, valor: g.total })),
        ...areas.filter((x) => x.padre_id === pid && !x.grupo_id).map((x) => ({ id: `a${x.id}`, etiqueta: x.nombre, valor: x.total })),
      ];
    } else {
      const gid = a.grupo.id;
      filas = areas.filter((x) => x.grupo_id === gid).map((x) => ({ id: `a${x.id}`, etiqueta: x.nombre, valor: x.total }));
    }
    return filas.sort((x, y) => y.valor - x.valor);
  });

  /** Summary rows (Django `pintarFicha`) */
  protected readonly ficha = computed<[string, string][]>(() => {
    const f = this.datos().ficha;
    const padre = f.nombre_padre;
    const filas: [string, string][] = [['Atenciones', num(f.casos)]];
    if (padre && f.pct_padre !== null) filas.push([`Del total de ${padre}`, `${num(f.pct_padre)}%`]);
    filas.push(['Fuera de turno', `${num(f.fuera)} (${num(f.fuera_pct)}%)`]);
    if (padre && f.delta_padre !== null) {
      filas.push([`Fuera de turno vs ${padre}`, `${f.delta_padre > 0 ? '+' : '−'}${num(Math.abs(f.delta_padre))} puntos`]);
    }
    filas.push(['Media por mes', `${num(f.promedio_mes)} en ${f.meses_activos} ${f.meses_activos === 1 ? 'mes' : 'meses'}`]);
    if (f.meses_activos > 1) {
      filas.push(['Mes más cargado', `${f.pico ?? '—'} · ${num(f.pico_total)} casos`]);
      filas.push(['Mes más tranquilo', `${f.valle ?? '—'} · ${num(f.valle_total)} casos`]);
    }
    filas.push(['Categoría más frecuente', `${f.dominante ?? '—'} (${num(f.dominante_pct)}%)`]);
    filas.push(['3 categorías más frecuentes', `${num(f.top3_pct)}% de las atenciones`]);
    return filas;
  });

  /** Weeks (columns, Monday first) × weekdays (rows) between the first and last day with cases */
  protected readonly calendario = computed(() => {
    const cal = this.datos().charts.calendario;
    if (!cal.inicio || !cal.fin) return null;
    const porDia = new Map(cal.datos);
    const inicio = fechaUtc(cal.inicio);
    const fin = fechaUtc(cal.fin);
    const lunes = new Date(inicio.getTime() - ((inicio.getUTCDay() + 6) % 7) * DIA_MS);
    const semanas = Math.floor((fin.getTime() - lunes.getTime()) / DIA_MS / 7) + 1;
    const valores: CeldaCalor[][] = DIAS.map(() => []);
    const titulos: string[][] = DIAS.map(() => []);
    const columnas: string[] = [];
    for (let s = 0; s < semanas; s++) {
      let etiqueta = '';
      for (let d = 0; d < 7; d++) {
        const dia = new Date(lunes.getTime() + (s * 7 + d) * DIA_MS);
        const iso = dia.toISOString().slice(0, 10);
        const dentro = dia >= inicio && dia <= fin;
        valores[d].push(dentro ? porDia.get(iso) ?? 0 : null);
        titulos[d].push(iso);
        if (dia.getUTCDate() === 1 || (s === 0 && d === 0)) etiqueta = MESES_CORTOS[dia.getUTCMonth()];
      }
      columnas.push(etiqueta);
    }
    return { columnas, valores, titulos };
  });

  /** Sankey links as two ranked steps: channel → category, category → sector */
  protected readonly flujo = computed(() => {
    const c = this.datos().charts;
    const medios = new Set(c.medio.labels);
    const filas = c.sankey.links.map((l) => ({ etiqueta: `${l.source} → ${l.target}`, valor: l.value, medio: medios.has(l.source) }));
    const orden = (xs: typeof filas) => xs.sort((a, b) => b.valor - a.valor).slice(0, 12);
    return { entrada: orden(filas.filter((f) => f.medio)), salida: orden(filas.filter((f) => !f.medio)) };
  });

  protected readonly topAreas = computed(() => this.datos().charts.top_areas.map((a) => ({ etiqueta: a.area, valor: a.total })));
  protected readonly categorias = computed(() => filasDeSerie(this.datos().charts.categoria));
  protected readonly rendimiento = computed(() => filasDeSerie(this.datos().charts.rendimiento));
  protected readonly colaboraciones = computed(() => filasDeSerie(this.datos().charts.colaboraciones));

  protected readonly puntos = computed<PuntoDispersion[]>(() =>
    this.datos().charts.scatter.datos.map(([x, y, nombre, pct]) => ({ x, y, nombre, nota: `${num(pct)}% fuera de turno` })));

  protected readonly perfil = computed(() => {
    const tecnicos = this.datos().charts.radar.tecnicos;
    return tecnicos.find((t) => t.id === this.tecnicoId()) ?? tecnicos[0] ?? null;
  });
  protected readonly maxRadar = computed(() =>
    Math.max(1, ...this.datos().charts.radar.tecnicos.flatMap((t) => t.valores)));

  /** categoria_mes cells ([mes, categoría, total]) as a categorías × meses matrix */
  protected readonly categoriaMes = computed<CeldaCalor[][]>(() => {
    const cm = this.datos().charts.categoria_mes;
    const m: CeldaCalor[][] = cm.categorias.map(() => cm.meses.map(() => 0));
    for (const [mes, cat, total] of cm.celdas) m[cat][mes] = total;
    return m;
  });

  protected readonly serieEvolucion = computed<SerieGrafico[]>(() => [
    { nombre: 'Atenciones', color: 'var(--serie-1)', valores: this.datos().charts.evolucion.values },
  ]);
}
