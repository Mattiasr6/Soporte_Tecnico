import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IconoComponent } from '../../compartido/icono.component';
import { hoyIso } from '../../core/fechas';
import { NotificacionesService } from '../../core/notificaciones.service';
import { PanelSoporteService, ReporteSoporte, VistaReporte } from '../../core/panel-soporte.service';
import { ReportesSoporteVistaComponent } from './reportes-soporte-vista.component';

/**
 * Monthly Soporte report (container), ported from Django `reportes_vista`.
 * The period lives in the URL (`?mes=YYYY-MM&vista=mes|anio`, current month
 * by default) so a report can be shared; the API computes the payload.
 * "Imprimir / Guardar PDF" prints only the report (print CSS in styles.css).
 */
@Component({
  selector: 'app-reportes-soporte',
  imports: [FormsModule, IconoComponent, ReportesSoporteVistaComponent],
  styles: `
    :host { --serie-1: #2a78d6; --serie-2: #eb6834; --serie-3: #1baf7a; --serie-4: #eda100; --serie-5: #e87ba4; --serie-6: #008300; }
    :host-context(.oscuro) { --serie-1: #3987e5; --serie-2: #d95926; --serie-3: #199e70; --serie-4: #c98500; --serie-5: #d55181; --serie-6: #008300; }
  `,
  template: `
    <div class="zona-reporte">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="text-2xl font-bold">Reporte mensual — Soporte Técnico</h1>
          @if (reporte(); as r) {
            <p class="mt-0.5 text-sm text-slate-600">{{ r.periodo.etiqueta }} · Equipo de Soporte Técnico · generado {{ r.metodologia.generado_en }}</p>
          }
        </div>
        <div class="no-imprimir flex flex-wrap items-end gap-2">
          <div>
            <label class="etiqueta" for="rep-mes">Mes</label>
            <input id="rep-mes" type="month" class="campo !w-44 !py-1.5" [(ngModel)]="mes">
          </div>
          <div class="flex rounded-md border border-slate-300 p-0.5 text-sm" role="radiogroup" aria-label="Vista">
            <button type="button" role="radio" class="rounded px-3 py-1" [attr.aria-checked]="vista() === 'mes'"
                    [class]="vista() === 'mes' ? 'bg-marca-600 text-white' : 'text-slate-600'" (click)="vista.set('mes')">Mes</button>
            <button type="button" role="radio" class="rounded px-3 py-1" [attr.aria-checked]="vista() === 'anio'"
                    [class]="vista() === 'anio' ? 'bg-marca-600 text-white' : 'text-slate-600'" (click)="vista.set('anio')">Acumulado del año</button>
          </div>
          <button class="btn-secundario btn-sm" (click)="ver()">Ver</button>
          <button class="btn-primario btn-sm" (click)="imprimir()" [disabled]="!reporte()"><app-icono nombre="imprimir" [tamano]="14" /> Imprimir / Guardar PDF</button>
        </div>
      </div>

      @if (reporte(); as r) {
        <app-reportes-soporte-vista [reporte]="r" />
      } @else if (cargando()) {
        <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
      } @else {
        <div class="tarjeta py-10 text-center text-sm text-slate-500">
          <p>No se pudo cargar el reporte. Reintentá.</p>
          <button class="btn-secundario btn-sm mt-3" (click)="cargar()">Reintentar</button>
        </div>
      }
    </div>
  `,
})
export class ReportesSoporteComponent implements OnInit {
  private readonly panel = inject(PanelSoporteService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected mes = hoyIso().slice(0, 7);
  protected readonly vista = signal<VistaReporte>('mes');
  protected readonly reporte = signal<ReporteSoporte | null>(null);
  protected readonly cargando = signal(false);

  ngOnInit(): void {
    // The URL owns the period: every change of ?mes/?vista reloads the report
    this.route.queryParamMap.subscribe((q) => {
      const mes = q.get('mes') ?? '';
      if (/^\d{4}-\d{2}$/.test(mes)) this.mes = mes;
      this.vista.set(q.get('vista') === 'anio' ? 'anio' : 'mes');
      void this.cargar();
    });
  }

  protected ver(): void {
    if (!/^\d{4}-\d{2}$/.test(this.mes ?? '')) return;
    void this.router.navigate([], { relativeTo: this.route, queryParams: { mes: this.mes, vista: this.vista() } });
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      const r = await this.panel.reporte(this.mes, this.vista());
      this.reporte.set(r);
      this.mes = r.periodo.mes;
    } catch (e) {
      this.reporte.set(null);
      this.notificaciones.error(e, 'No se cargó el reporte');
    } finally {
      this.cargando.set(false);
    }
  }

  protected imprimir(): void {
    document.body.classList.add('imprimiendo-reporte');
    window.addEventListener('afterprint', () => document.body.classList.remove('imprimiendo-reporte'), { once: true });
    window.print();
  }
}
