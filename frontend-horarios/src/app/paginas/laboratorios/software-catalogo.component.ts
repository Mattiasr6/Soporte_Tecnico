import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { LicenciaSoftware, Software } from '../../core/modelos';

const COLOR_LICENCIA: Record<LicenciaSoftware, string> = {
  gratuita: 'bg-emerald-50 text-emerald-700',
  mixta: 'bg-sky-50 text-sky-700',
  paga: 'bg-amber-50 text-amber-800',
};

/**
 * Software catalogue table (presentational), like the Django "Catálogo" card:
 * name with esencial/docentes/inactivo tags and uso, licence, number of labs.
 * Edit and delete buttons only when `puedeEditar`.
 */
@Component({
  selector: 'app-software-catalogo',
  imports: [IconoComponent],
  template: `
    <div class="overflow-x-auto rounded-xl border border-slate-200">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th class="px-3 py-2 font-semibold">Nombre</th>
            <th class="px-3 py-2 font-semibold">Licencia</th>
            <th class="px-3 py-2 text-right font-semibold">Labs</th>
            @if (puedeEditar()) { <th class="px-3 py-2"></th> }
          </tr>
        </thead>
        <tbody>
          @for (s of software(); track s.id) {
            <tr class="border-t border-slate-100" [class.opacity-60]="!s.activo">
              <td class="px-3 py-2">
                <p class="font-medium">{{ s.nombre }}</p>
                <p class="mt-0.5 flex flex-wrap items-center gap-1 text-xs">
                  @if (s.esencial) { <span class="chip bg-marca-50 text-marca-700">esencial</span> }
                  @if (s.docentes) { <span class="chip bg-indigo-50 text-indigo-700">docentes</span> }
                  @if (!s.activo) { <span class="chip bg-slate-100 text-slate-500">inactivo</span> }
                  @if (s.uso) { <span class="text-slate-500">{{ s.uso }}</span> }
                </p>
              </td>
              <td class="px-3 py-2"><span class="chip" [class]="colorLicencia[s.licencia]">{{ s.licencia }}</span></td>
              <td class="px-3 py-2 text-right tabular-nums">{{ s.ambientes.length }}</td>
              @if (puedeEditar()) {
                <td class="px-3 py-2 text-right whitespace-nowrap">
                  <button class="btn-fantasma btn-sm" (click)="editar.emit(s)" title="Editar" aria-label="Editar programa"><app-icono nombre="editar" [tamano]="15" /></button>
                  <button class="btn-fantasma btn-sm text-red-600" (click)="eliminar.emit(s)" title="Eliminar" aria-label="Eliminar programa"><app-icono nombre="eliminar" [tamano]="15" /></button>
                </td>
              }
            </tr>
          } @empty {
            <tr><td class="px-3 py-8 text-center text-slate-500" [attr.colspan]="puedeEditar() ? 4 : 3">{{ vacio() }}</td></tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class SoftwareCatalogoComponent {
  readonly software = input.required<Software[]>();
  readonly puedeEditar = input(false);
  readonly vacio = input('Catálogo vacío.');
  readonly editar = output<Software>();
  readonly eliminar = output<Software>();

  protected readonly colorLicencia = COLOR_LICENCIA;
}
