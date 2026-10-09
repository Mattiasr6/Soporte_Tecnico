import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { CambioAuditoria } from '../../core/auditoria.service';

/** Badge color per action (crear / editar / eliminar) */
const CLASE_ACCION: Record<string, string> = {
  crear: 'bg-emerald-100 text-emerald-700',
  editar: 'bg-sky-100 text-sky-700',
  eliminar: 'bg-red-100 text-red-700',
};

/**
 * Tabla de cambios de la auditoría (presentacional): cuándo, quién, acción,
 * entidad y detalle. En el celular cada fila se ve como una ficha.
 */
@Component({
  selector: 'app-auditoria-tabla',
  imports: [DatePipe],
  template: `
    @if (filas().length) {
      <div class="tarjeta hidden overflow-x-auto md:block">
        <table class="tabla">
          <thead>
            <tr><th>Cuándo</th><th>Quién</th><th>Acción</th><th>Entidad</th><th>Detalle</th></tr>
          </thead>
          <tbody>
            @for (f of filas(); track f.id) {
              <tr>
                <td class="whitespace-nowrap text-xs text-slate-500">{{ f.fecha | date: 'dd/MM/yyyy HH:mm' }}</td>
                <td>
                  {{ f.usuario_nombre || f.usuario_email }}
                  <span class="block text-xs text-slate-500">{{ f.rol }}@if (f.entidad_id) { · #{{ f.entidad_id }} }</span>
                </td>
                <td><span class="chip" [class]="claseAccion(f.accion)">{{ f.accion }}</span></td>
                <td>{{ f.entidad }}</td>
                <td class="font-mono text-xs break-words text-slate-600">{{ f.detalle || '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <ul class="space-y-2 md:hidden">
        @for (f of filas(); track f.id) {
          <li class="tarjeta space-y-1 p-3 text-sm">
            <div class="flex items-center justify-between gap-2">
              <span class="chip" [class]="claseAccion(f.accion)">{{ f.accion }}</span>
              <span class="text-xs text-slate-500">{{ f.fecha | date: 'dd/MM/yyyy HH:mm' }}</span>
            </div>
            <p><b>{{ f.entidad }}</b>@if (f.entidad_id) { <span class="text-slate-500"> #{{ f.entidad_id }}</span> }</p>
            <p class="text-xs text-slate-500">{{ f.usuario_nombre || f.usuario_email }} · {{ f.rol }}</p>
            <p class="font-mono text-xs break-words text-slate-600">{{ f.detalle || '—' }}</p>
          </li>
        }
      </ul>
    } @else {
      <div class="tarjeta p-6 text-center text-sm text-slate-500">Sin cambios registrados todavía.</div>
    }
  `,
})
export class AuditoriaTablaComponent {
  readonly filas = input.required<CambioAuditoria[]>();

  protected claseAccion(accion: string): string {
    return CLASE_ACCION[accion] ?? 'bg-slate-100 text-slate-600';
  }
}
