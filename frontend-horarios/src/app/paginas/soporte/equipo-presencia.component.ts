import { Component, input } from '@angular/core';
import { ETIQUETAS_PRESENCIA, ORDEN_PRESENCIA, PresenciaEquipo } from '../../core/inicio-soporte.service';
import { EstadoPresenciaChipComponent } from './estado-presencia-chip.component';

/**
 * "El equipo ahora" (presentational): how many technicians are in each state
 * and one card per person with role, today's shift, attentions and entry time.
 */
@Component({
  selector: 'app-equipo-presencia',
  imports: [EstadoPresenciaChipComponent],
  template: `
    <div class="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
      @for (e of orden; track e) {
        <div class="tarjeta flex items-center justify-between px-3 py-2">
          <span class="text-sm text-slate-600">{{ etiquetas[e] }}</span>
          <b class="text-lg">{{ presencia()?.conteo?.[e] ?? 0 }}</b>
        </div>
      }
    </div>
    @if (presencia()?.tecnicos?.length) {
      <div class="grid gap-2 md:grid-cols-2">
        @for (t of presencia()!.tecnicos; track t.id) {
          <div class="tarjeta flex items-center justify-between gap-3 px-3 py-2">
            <div class="min-w-0">
              <p class="truncate font-medium">{{ t.display_name }}</p>
              <p class="text-xs text-slate-500">
                {{ t.role }}{{ t.horario_hoy ? ' · ' + t.horario_hoy : '' }} · {{ t.atenciones_hoy }} hoy{{ t.entra_a_las ? ' · entra ' + t.entra_a_las : '' }}
              </p>
            </div>
            <app-estado-presencia-chip [estado]="t.estado_actual" />
          </div>
        }
      </div>
    } @else {
      <p class="text-sm text-slate-500">No hay técnicos activos.</p>
    }
  `,
})
export class EquipoPresenciaComponent {
  readonly presencia = input<PresenciaEquipo | null>(null);

  protected readonly orden = ORDEN_PRESENCIA;
  protected readonly etiquetas = ETIQUETAS_PRESENCIA;
}
