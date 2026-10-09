import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { AtencionSoporte } from '../../core/soporte.service';

/**
 * Listado de atenciones de Soporte (presentacional): fecha, área, categoría,
 * técnico y si fue fuera de turno. En el celular cada fila es una ficha.
 */
@Component({
  selector: 'app-atenciones-soporte-tabla',
  imports: [IconoComponent],
  template: `
    <div class="tarjeta hidden overflow-x-auto md:block">
      <table class="tabla">
        <thead>
          <tr><th>Fecha</th><th>Área</th><th>Categoría</th><th>Técnico</th><th>Fuera de turno</th><th></th></tr>
        </thead>
        <tbody>
          @for (a of atenciones(); track a.id) {
            <tr>
              <td class="whitespace-nowrap">{{ a.fecha_registro }}</td>
              <td>{{ a.area_solicitante }}</td>
              <td>{{ a.categoria }}</td>
              <td>{{ a.usuario_nombre }}</td>
              <td>@if (a.fuera_de_turno) { <span class="chip bg-amber-100 text-amber-800">fuera turno</span> }</td>
              <td class="text-right">
                <button class="btn-fantasma btn-sm" type="button" title="Ver detalle" [attr.aria-label]="'Ver detalle de la atención ' + a.id" (click)="ver.emit(a)">
                  <app-icono nombre="ver" [tamano]="16" />
                </button>
              </td>
            </tr>
          } @empty {
            <tr><td colspan="6" class="text-slate-500">Sin registros.</td></tr>
          }
        </tbody>
      </table>
    </div>
    <ul class="space-y-2 md:hidden">
      @for (a of atenciones(); track a.id) {
        <li class="tarjeta flex items-start gap-2 p-3 text-sm">
          <dl class="min-w-0 flex-1 space-y-0.5">
            <div class="flex gap-2"><dt class="w-28 text-slate-500">Fecha</dt><dd class="font-medium">{{ a.fecha_registro }}</dd></div>
            <div class="flex gap-2"><dt class="w-28 text-slate-500">Área</dt><dd class="font-medium">{{ a.area_solicitante }}</dd></div>
            <div class="flex gap-2"><dt class="w-28 text-slate-500">Categoría</dt><dd class="font-medium">{{ a.categoria }}</dd></div>
            <div class="flex gap-2"><dt class="w-28 text-slate-500">Técnico</dt><dd class="font-medium">{{ a.usuario_nombre }}</dd></div>
            @if (a.fuera_de_turno) { <span class="chip bg-amber-100 text-amber-800">fuera turno</span> }
          </dl>
          <button class="btn-fantasma btn-sm" type="button" title="Ver detalle" [attr.aria-label]="'Ver detalle de la atención ' + a.id" (click)="ver.emit(a)">
            <app-icono nombre="ver" [tamano]="16" />
          </button>
        </li>
      } @empty {
        <li class="tarjeta p-3 text-sm text-slate-500">Sin registros.</li>
      }
    </ul>
  `,
})
export class AtencionesSoporteTablaComponent {
  readonly atenciones = input.required<AtencionSoporte[]>();
  readonly ver = output<AtencionSoporte>();
}
