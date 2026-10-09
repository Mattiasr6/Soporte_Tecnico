import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IconoComponent } from '../../compartido/icono.component';
import { ApiService } from '../../core/api.service';
import { CatalogosService } from '../../core/catalogos.service';
import { descargarCsv } from '../../core/exportar';
import { hoyIso } from '../../core/fechas';
import { TurnoCodigo } from '../../core/modelos';
import { NotificacionesService } from '../../core/notificaciones.service';
import { TURNOS_TICKET } from '../../core/tickets';
import {
  DashboardLaboratorios, DashboardLaboratoriosVistaComponent, NOMBRE_TURNO, nombreTipo,
} from './dashboard-laboratorios-vista.component';

/** First and last day of a "YYYY-MM" month */
function rangoMes(mes: string): { desde: string; hasta: string } {
  const [a, m] = mes.split('-').map(Number);
  const ultimo = new Date(a, m, 0).getDate();
  return { desde: `${mes}-01`, hasta: `${mes}-${String(ultimo).padStart(2, '0')}` };
}

/**
 * Lab dashboard and reports (container), ported from Django
 * `lab_dashboard_vista` + `lab_reportes_vista`: one month, optionally narrowed
 * to a turno and a lab. Data comes from horarios.fn_dashboard_laboratorios.
 */
@Component({
  selector: 'app-dashboard-laboratorios',
  imports: [FormsModule, RouterLink, IconoComponent, DashboardLaboratoriosVistaComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Laboratorios por turno</h1>
        <p class="mt-0.5 text-sm text-slate-600">Atenciones del mes por laboratorio, categoría, turno y medio de solicitud.
          <a routerLink="/desempeno" class="text-marca-600 hover:underline">Ver desempeño</a></p>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <div>
          <label class="etiqueta">Mes</label>
          <input type="month" class="campo !w-44 !py-1.5" [ngModel]="mes()" (ngModelChange)="cambiarMes($event)">
        </div>
        <div>
          <label class="etiqueta">Turno</label>
          <select class="campo !w-32 !py-1.5" [ngModel]="turno()" (ngModelChange)="turno.set($event); cargar()">
            <option [ngValue]="null">Todos</option>
            @for (t of turnos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }
          </select>
        </div>
        <div>
          <label class="etiqueta">Laboratorio</label>
          <select class="campo !w-36 !py-1.5" [ngModel]="lab()" (ngModelChange)="lab.set($event); cargar()">
            <option [ngValue]="null">Todos</option>
            @for (l of laboratorios(); track l.id) { <option [ngValue]="l.id">{{ l.codigo }}</option> }
          </select>
        </div>
        <button class="btn-secundario btn-sm" (click)="cambiarMes(mesActual)" [disabled]="mes() === mesActual">Este mes</button>
        <button class="btn-secundario btn-sm" (click)="exportar()" [disabled]="!datos()"><app-icono nombre="descargar" [tamano]="14" /> Exportar</button>
      </div>
    </header>

    @if (datos(); as d) {
      <app-dashboard-laboratorios-vista [datos]="d" />
    } @else if (cargando()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">No se pudo cargar el dashboard.</p>
    }
  `,
})
export class DashboardLaboratoriosComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly catalogos = inject(CatalogosService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly turnos = TURNOS_TICKET;
  protected readonly mesActual = hoyIso().slice(0, 7);
  protected readonly mes = signal(this.mesActual);
  protected readonly turno = signal<TurnoCodigo | null>(null);
  protected readonly lab = signal<number | null>(null);
  protected readonly datos = signal<DashboardLaboratorios | null>(null);
  protected readonly cargando = signal(false);
  protected readonly laboratorios = computed(() => this.catalogos.laboratorios());

  ngOnInit(): void {
    void this.cargar();
  }

  protected cambiarMes(mes: string): void {
    if (!/^\d{4}-\d{2}$/.test(mes ?? '')) return;
    this.mes.set(mes);
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    const params: Record<string, string | number> = rangoMes(this.mes());
    const turno = this.turno();
    const lab = this.lab();
    if (turno) params['turno'] = turno;
    if (lab) params['ambiente_id'] = lab;
    this.cargando.set(true);
    try {
      this.datos.set(await this.api.get<DashboardLaboratorios>('/dashboard/laboratorios', params));
    } catch (e) {
      this.datos.set(null);
      this.notificaciones.error(e, 'No se cargó el dashboard de laboratorios');
    } finally {
      this.cargando.set(false);
    }
  }

  /** Per-lab table as CSV (Django lab_export_csv covers the raw rows) */
  protected exportar(): void {
    const d = this.datos();
    if (!d) return;
    const filas = d.por_lab.map((l) => [l.codigo, l.total, nombreTipo(l.top_tipo), NOMBRE_TURNO[l.top_turno] ?? '']);
    descargarCsv(`laboratorios-${this.mes()}`, ['Laboratorio', 'Atenciones', 'Categoría principal', 'Turno principal'], filas);
  }
}
