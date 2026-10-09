import { Component, input, output } from '@angular/core';
import { Perfil } from '../../core/modelos';

/**
 * Team members with their Soporte role, Encargado or Auxiliar (presentational),
 * like Django's encargado toggle on the team list. The toggle is only enabled
 * when the page says the viewer may change roles.
 */
@Component({
  selector: 'app-encargados-equipo',
  template: `
    <div class="tarjeta overflow-x-auto">
      <table class="tabla">
        <thead><tr><th>Persona</th><th>Rol</th><th class="text-right">Encargado</th></tr></thead>
        <tbody>
          @for (m of miembros(); track m.id) {
            <tr>
              <td>
                <p class="font-medium">{{ m.nombre_completo }}</p>
                <p class="text-xs text-slate-500">{{ m.correo }}</p>
              </td>
              <td>
                <span class="chip" [class]="m.rol === 'encargado' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-200 text-slate-600'">
                  {{ m.rol === 'encargado' ? 'Encargado' : 'Auxiliar' }}
                </span>
              </td>
              <td class="text-right">
                <button type="button" role="switch" class="inline-flex h-6 w-11 items-center rounded-full p-0.5 transition disabled:cursor-not-allowed disabled:opacity-50"
                        [class]="m.rol === 'encargado' ? 'bg-marca-600' : 'bg-slate-300'"
                        [attr.aria-checked]="m.rol === 'encargado'" [attr.aria-label]="'Encargado: ' + m.nombre_completo"
                        [disabled]="!puedeCambiar() || cambiando() === m.id" (click)="alternar.emit(m)">
                  <span class="h-5 w-5 rounded-full bg-white shadow transition" [class.translate-x-5]="m.rol === 'encargado'"></span>
                </button>
              </td>
            </tr>
          } @empty {
            <tr><td colspan="3" class="py-6 text-center text-sm text-slate-500">No hay auxiliares ni encargados activos.</td></tr>
          }
        </tbody>
      </table>
      @if (!puedeCambiar()) {
        <p class="px-3 py-2 text-xs text-slate-400">Solo el Jefe puede cambiar quién es encargado.</p>
      }
    </div>
  `,
})
export class EncargadosEquipoComponent {
  readonly miembros = input<Perfil[]>([]);
  /** Only the Jefe may change Soporte roles (users endpoint, fn_es_admin) */
  readonly puedeCambiar = input(false);
  /** Member whose role is being saved */
  readonly cambiando = input<string | null>(null);
  readonly alternar = output<Perfil>();
}
