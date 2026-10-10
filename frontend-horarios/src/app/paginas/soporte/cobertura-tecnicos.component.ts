import { Component, input } from '@angular/core';
import { FranjaCobertura } from '../../core/horarios-tecnicos.service';

/**
 * Cobertura de un día tipo (presentacional): los 4 bloques fijos del día y
 * qué técnicos cubren cada uno, o "nadie".
 */
@Component({
  selector: 'app-cobertura-tecnicos',
  template: `
    <h3 class="mb-1 text-sm font-semibold">{{ titulo() }}</h3>
    <table class="w-full text-sm">
      <thead class="text-left text-xs text-slate-500">
        <tr><th class="py-1.5 pr-3 font-medium">Bloque</th><th class="py-1.5 pr-3 font-medium">Horario</th><th class="py-1.5 font-medium">Técnicos</th></tr>
      </thead>
      <tbody>
        @for (f of franjas(); track f.franja) {
          <tr class="border-t border-slate-100">
            <td class="py-1.5 pr-3">{{ f.franja }}</td>
            <td class="py-1.5 pr-3 text-xs whitespace-nowrap text-slate-500">{{ f.hora }}</td>
            <td class="py-1.5">
              @if (f.tecnicos.length) { {{ f.tecnicos.join(' · ') }} } @else { <span class="chip bg-red-100 text-red-700">nadie</span> }
            </td>
          </tr>
        }
      </tbody>
    </table>
  `,
})
export class CoberturaTecnicosComponent {
  readonly titulo = input('');
  readonly franjas = input<FranjaCobertura[]>([]);
}
