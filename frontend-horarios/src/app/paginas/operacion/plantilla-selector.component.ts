import { Component, computed, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { PlantillaAtencion, TipoPlantilla } from '../../core/modelos';
import { TIPOS_TICKET } from '../../core/tickets';

/**
 * Template picker of the attention form (presentational): the active
 * templates grouped by attention tipo. Choosing one emits it and the select
 * goes back to the placeholder, so the same template can be applied again.
 */
@Component({
  selector: 'app-plantilla-selector',
  imports: [IconoComponent],
  template: `
    <div class="flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
      <label class="flex items-center gap-1.5 text-sm font-medium text-slate-600" for="plantilla-atencion">
        <app-icono nombre="plantilla" [tamano]="15" /> Usar una plantilla
      </label>
      <select id="plantilla-atencion" class="campo !w-auto min-w-56 flex-1 !py-1" (change)="elegir($event)">
        <option value="">— elegir —</option>
        @for (g of grupos(); track g.tipo) {
          <optgroup [label]="g.texto">
            @for (p of g.plantillas; track p.id) { <option [value]="p.id">{{ p.nombre }}</option> }
          </optgroup>
        }
      </select>
    </div>
  `,
})
export class PlantillaSelectorComponent {
  readonly plantillas = input.required<PlantillaAtencion[]>();
  readonly aplicar = output<PlantillaAtencion>();

  protected readonly grupos = computed(() => {
    const tipos: TipoPlantilla[] = ['programas', 'preventivo', 'docente', 'personal'];
    return tipos
      .map((tipo) => ({ tipo, texto: TIPOS_TICKET[tipo].texto, plantillas: this.plantillas().filter((p) => p.tipo === tipo) }))
      .filter((g) => g.plantillas.length);
  });

  protected elegir(evento: Event): void {
    const select = evento.target as HTMLSelectElement;
    const elegida = this.plantillas().find((p) => String(p.id) === select.value);
    select.value = '';
    if (elegida) this.aplicar.emit(elegida);
  }
}
