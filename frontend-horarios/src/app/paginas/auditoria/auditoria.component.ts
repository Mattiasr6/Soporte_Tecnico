import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ACCIONES_AUDITORIA, AuditoriaService, CambioAuditoria, ENTIDADES_AUDITORIA, FiltroAuditoria,
} from '../../core/auditoria.service';
import { AuditoriaTablaComponent } from './auditoria-tabla.component';

/**
 * Auditoría de cambios (solo lectura): qué se creó, editó o borró. La ven el
 * Jefe y quien tiene dashboard; el backend es quien decide (403 al resto).
 */
@Component({
  selector: 'app-auditoria',
  imports: [FormsModule, AuditoriaTablaComponent],
  template: `
    <header class="mb-4">
      <h1 class="text-2xl font-bold">Auditoría de cambios</h1>
      <p class="text-sm text-slate-500">Rastro de cambios esenciales: qué se creó, qué se editó y qué se borró. Visible solo para Jefes.</p>
    </header>

    <div class="mb-3 flex flex-wrap items-end gap-2">
      <div>
        <label class="etiqueta" for="au-entidad">Entidad</label>
        <select class="campo !w-44 !py-1.5" id="au-entidad" [ngModel]="filtro().entidad" (ngModelChange)="filtrar({ entidad: $event })">
          <option value="">— todas —</option>
          @for (e of entidades; track e) { <option [value]="e">{{ e }}</option> }
        </select>
      </div>
      <div>
        <label class="etiqueta" for="au-accion">Acción</label>
        <select class="campo !w-36 !py-1.5" id="au-accion" [ngModel]="filtro().accion" (ngModelChange)="filtrar({ accion: $event })">
          <option value="">— todas —</option>
          @for (a of acciones; track a) { <option [value]="a">{{ a }}</option> }
        </select>
      </div>
      <button class="btn-secundario btn-sm" type="button" (click)="limpiar()" [disabled]="!filtro().entidad && !filtro().accion">Limpiar</button>
      <span class="text-xs text-slate-500">{{ filas().length }} registro{{ filas().length === 1 ? '' : 's' }}</span>
    </div>

    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (error()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudo cargar la auditoría: {{ error() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <app-auditoria-tabla [filas]="filas()" />
    }
  `,
})
export class AuditoriaComponent implements OnInit {
  private readonly auditoria = inject(AuditoriaService);

  protected readonly entidades = ENTIDADES_AUDITORIA;
  protected readonly acciones = ACCIONES_AUDITORIA;
  protected readonly filtro = signal<FiltroAuditoria>({ entidad: '', accion: '' });
  protected readonly filas = signal<CambioAuditoria[]>([]);
  protected readonly cargando = signal(true);
  protected readonly error = signal('');

  ngOnInit(): void {
    void this.cargar();
  }

  /** Like the Django select (`onchange=submit`): every change reloads */
  protected filtrar(cambio: Partial<FiltroAuditoria>): void {
    this.filtro.update((f) => ({ ...f, ...cambio }));
    void this.cargar();
  }

  protected limpiar(): void {
    this.filtro.set({ entidad: '', accion: '' });
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.error.set('');
    try {
      this.filas.set(await this.auditoria.listar(this.filtro()));
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }
}
