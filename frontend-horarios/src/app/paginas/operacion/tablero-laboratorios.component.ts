import { Component, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { IconoComponent } from '../../compartido/icono.component';
import { ApiService } from '../../core/api.service';
import { fechaActual } from '../../core/fechas';
import { NotificacionesService } from '../../core/notificaciones.service';
import { PanelesService } from '../../core/paneles.service';
import { TableroLaboratoriosVistaComponent, TarjetaLaboratorio } from './tablero-laboratorios-vista.component';

/**
 * Lab traffic-light board (container), ported from Django `lab_tablero_vista`.
 * GET /tablero-laboratorios computes the state of each lab:
 * red = lost objects in custody (not expired), yellow = a PC attended in the
 * last 7 days, PCs in maintenance/decommissioned or a pending decommission
 * request, green = none of those. Card actions open the existing screens.
 */
@Component({
  selector: 'app-tablero-laboratorios',
  imports: [RouterLink, IconoComponent, TableroLaboratoriosVistaComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Tablero de laboratorios</h1>
        <p class="mt-0.5 text-sm text-slate-600">
          Rojo: objetos perdidos en custodia. Amarillo: PCs atendidas en los últimos 7 días, en mantenimiento, de baja o con solicitud de baja. Verde: sin novedades.
          <a routerLink="/timeline" class="text-marca-600 hover:underline">Ver actividad del día</a>
        </p>
      </div>
      <button class="btn-secundario btn-sm" (click)="cargar()" [disabled]="cargando()">
        <app-icono nombre="restaurar" [tamano]="14" /> Actualizar
      </button>
    </header>

    @if (tarjetas(); as t) {
      <app-tablero-laboratorios-vista [tarjetas]="t"
        (croquis)="abrirCroquis($event)" (atenciones)="irA('/atenciones', $event)" (objetos)="irA('/objetos-perdidos', $event)" />
    } @else if (cargando()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">No se pudo cargar el tablero.</p>
    }
  `,
})
export class TableroLaboratoriosComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly paneles = inject(PanelesService);
  private readonly router = inject(Router);

  protected readonly tarjetas = signal<TarjetaLaboratorio[] | null>(null);
  protected readonly cargando = signal(false);

  ngOnInit(): void {
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      this.tarjetas.set(await this.api.get<TarjetaLaboratorio[]>('/tablero-laboratorios'));
    } catch (e) {
      this.tarjetas.set(null);
      this.notificaciones.error(e, 'No se cargó el tablero de laboratorios');
    } finally {
      this.cargando.set(false);
    }
  }

  protected abrirCroquis(ambienteId: number): void {
    this.paneles.abrirLaboratorio(ambienteId, fechaActual(environment.zonaHoraria), 'croquis');
  }

  /** Opens a list page filtered by the lab (`?lab=` is bound to its input) */
  protected irA(ruta: string, ambienteId: number): void {
    void this.router.navigate([ruta], { queryParams: { lab: ambienteId } });
  }
}
