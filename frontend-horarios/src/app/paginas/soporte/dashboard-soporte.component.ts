import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FilaRanking } from '../../compartido/barras-ranking.component';
import { NotificacionesService } from '../../core/notificaciones.service';
import { DashboardSoporte, PanelSoporteService } from '../../core/panel-soporte.service';
import { AlcanceDashboard, DashboardSoporteVistaComponent, NivelAlcance } from './dashboard-soporte-vista.component';

const SIN_ALCANCE: AlcanceDashboard = { padre: null, grupo: null, area: null };

/**
 * Soporte dashboard (container), ported from Django `dashboard_vista` and its
 * `panel/stats/` reload: a month range plus the sector › dependency › area
 * drill-down. Every change asks GET /api/atenciones/dashboard again, which
 * computes the charts and the summary (Jefe or dashboard flag only).
 */
@Component({
  selector: 'app-dashboard-soporte',
  imports: [FormsModule, DashboardSoporteVistaComponent],
  styles: `
    :host { --serie-1: #2a78d6; --serie-2: #eb6834; --serie-3: #1baf7a; --serie-4: #eda100; --serie-5: #e87ba4; --serie-6: #008300; }
    :host-context(.oscuro) { --serie-1: #3987e5; --serie-2: #d95926; --serie-3: #199e70; --serie-4: #c98500; --serie-5: #d55181; --serie-6: #008300; }
  `,
  template: `
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Dashboard</h1>
        <p class="mt-0.5 text-sm text-slate-600">Haz clic en una barra para filtrar: todo el tablero se recalcula</p>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <div>
          <label class="etiqueta" for="dash-desde">Desde</label>
          <input id="dash-desde" type="month" class="campo !w-44 !py-1.5" [(ngModel)]="desde">
        </div>
        <div>
          <label class="etiqueta" for="dash-hasta">Hasta</label>
          <input id="dash-hasta" type="month" class="campo !w-44 !py-1.5" [(ngModel)]="hasta">
        </div>
        <button class="btn-primario btn-sm" (click)="aplicar()">Aplicar</button>
        <button class="btn-secundario btn-sm" (click)="reiniciar()">Reiniciar</button>
      </div>
    </div>
    @if (errorFiltro()) { <p class="mb-3 text-sm text-red-700">{{ errorFiltro() }}</p> }

    @if (datos(); as d) {
      <div [class.opacity-60]="cargando()">
        <app-dashboard-soporte-vista [datos]="d" [alcance]="alcance()" (elegir)="elegir($event)" (quitar)="quitar($event)" (limpiar)="limpiar()" />
      </div>
    } @else if (cargando()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else {
      <div class="tarjeta py-10 text-center text-sm text-slate-500">
        <p>No se pudo cargar el dashboard.</p>
        <button class="btn-secundario btn-sm mt-3" (click)="cargar()">Reintentar</button>
      </div>
    }
  `,
})
export class DashboardSoporteComponent implements OnInit {
  private readonly panel = inject(PanelSoporteService);
  private readonly notificaciones = inject(NotificacionesService);

  protected desde = '';
  protected hasta = '';
  /** Range applied to the data (the inputs only count after "Aplicar") */
  private readonly rango = signal({ desde: '', hasta: '' });
  protected readonly alcance = signal<AlcanceDashboard>(SIN_ALCANCE);
  protected readonly datos = signal<DashboardSoporte | null>(null);
  protected readonly cargando = signal(false);
  protected readonly errorFiltro = signal('');

  ngOnInit(): void {
    void this.cargar();
  }

  protected aplicar(): void {
    if (this.desde && this.hasta && this.desde > this.hasta) {
      this.errorFiltro.set('El mes Desde no puede ser posterior al mes Hasta.');
      return;
    }
    this.errorFiltro.set('');
    this.rango.set({ desde: this.desde, hasta: this.hasta });
    void this.cargar();
  }

  /** Django "Reiniciar": no range, no drill-down */
  protected reiniciar(): void {
    this.desde = '';
    this.hasta = '';
    this.errorFiltro.set('');
    this.rango.set({ desde: '', hasta: '' });
    this.alcance.set(SIN_ALCANCE);
    void this.cargar();
  }

  /** Drill-down click: a sector enters it, a dependency goes one level down, an area filters */
  protected elegir(f: FilaRanking): void {
    const clave = String(f.id ?? '');
    const id = Number(clave.slice(1));
    const nodo = { id, nombre: f.etiqueta };
    const a = this.alcance();
    if (clave.startsWith('p')) this.alcance.set({ padre: nodo, grupo: null, area: null });
    else if (clave.startsWith('g')) this.alcance.set({ ...a, grupo: nodo, area: null });
    else if (clave.startsWith('a')) this.alcance.set({ ...a, area: nodo });
    else return;
    void this.cargar();
  }

  protected quitar(nivel: NivelAlcance): void {
    const a = this.alcance();
    if (nivel === 'padre') this.alcance.set(SIN_ALCANCE);
    else if (nivel === 'grupo') this.alcance.set({ ...a, grupo: null, area: null });
    else this.alcance.set({ ...a, area: null });
    void this.cargar();
  }

  protected limpiar(): void {
    this.alcance.set(SIN_ALCANCE);
    void this.cargar();
  }

  /** Id of the latest request, so a slow older answer never overwrites a newer one */
  private pedido = 0;

  protected async cargar(): Promise<void> {
    const a = this.alcance();
    const actual = ++this.pedido;
    this.cargando.set(true);
    try {
      const datos = await this.panel.dashboard({
        ...this.rango(),
        grupo_padre_id: a.padre?.id ?? null,
        grupo_id: a.grupo?.id ?? null,
        area_id: a.area?.id ?? null,
      });
      if (actual === this.pedido) this.datos.set(datos);
    } catch (e) {
      if (actual !== this.pedido) return;
      this.datos.set(null);
      this.notificaciones.error(e, 'No se cargó el dashboard');
    } finally {
      if (actual === this.pedido) this.cargando.set(false);
    }
  }
}
