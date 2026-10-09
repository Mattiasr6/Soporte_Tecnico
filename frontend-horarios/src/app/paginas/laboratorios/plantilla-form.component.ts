import { Component, input, OnInit, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PlantillaAtencion, PlantillaNueva, TipoPlantilla } from '../../core/modelos';
import { TIPOS_TICKET, TURNOS_TICKET } from '../../core/tickets';

/** Attention tipos a template can prefill, with the attention form labels */
export const TIPOS_PLANTILLA: { valor: TipoPlantilla; texto: string }[] = (
  ['programas', 'preventivo', 'docente', 'personal'] as TipoPlantilla[]
).map((valor) => ({ valor, texto: TIPOS_TICKET[valor].texto }));

/**
 * Attention template form (presentational), Django "Plantillas de atención":
 * nombre, tipo (Django's categoría), turno, activa, descripción and solución.
 */
@Component({
  selector: 'app-plantilla-form',
  imports: [FormsModule],
  template: `
    <form class="grid gap-3 sm:grid-cols-2" [id]="idForm()" (ngSubmit)="enviar()">
      <div class="sm:col-span-2">
        <label class="etiqueta" for="pl-nombre">Nombre *</label>
        <input id="pl-nombre" class="campo" maxlength="100" [(ngModel)]="datos.nombre" name="nombre" placeholder="Ej: Instalar Office" required>
      </div>
      <div>
        <label class="etiqueta" for="pl-tipo">Tipo de atención</label>
        <select id="pl-tipo" class="campo" [(ngModel)]="datos.tipo" name="tipo">
          @for (t of tipos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }
        </select>
      </div>
      <div>
        <label class="etiqueta" for="pl-turno">Turno</label>
        <select id="pl-turno" class="campo" [(ngModel)]="datos.turno" name="turno">
          <option [ngValue]="null">— (el del momento)</option>
          @for (t of turnos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }
        </select>
      </div>
      <div class="sm:col-span-2">
        <label class="etiqueta" for="pl-desc">Descripción</label>
        <textarea id="pl-desc" class="campo" rows="2" maxlength="500" [(ngModel)]="datos.descripcion" name="descripcion"
                  [placeholder]="datos.tipo === 'programas' ? 'Programa(s) y versión, ej: Office 2021' : 'Qué se pidió o qué pasó'"></textarea>
      </div>
      <div class="sm:col-span-2">
        <label class="etiqueta" for="pl-sol">Solución</label>
        <textarea id="pl-sol" class="campo" rows="2" maxlength="1000" [(ngModel)]="datos.solucion" name="solucion" placeholder="Qué se hizo"></textarea>
      </div>
      <label class="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" [(ngModel)]="datos.activa" name="activa"> Activa (aparece en el formulario de atenciones)</label>
    </form>
  `,
})
export class PlantillaFormComponent implements OnInit {
  readonly idForm = input.required<string>();
  readonly inicial = input<PlantillaAtencion | null>(null);
  readonly guardar = output<PlantillaNueva>();

  protected readonly tipos = TIPOS_PLANTILLA;
  protected readonly turnos = TURNOS_TICKET;
  protected datos: PlantillaNueva = { nombre: '', tipo: 'programas', descripcion: '', solucion: '', turno: null, activa: true };

  ngOnInit(): void {
    const p = this.inicial();
    if (p) {
      this.datos = { nombre: p.nombre, tipo: p.tipo, descripcion: p.descripcion, solucion: p.solucion, turno: p.turno, activa: p.activa };
    }
  }

  protected enviar(): void {
    const d = this.datos;
    this.guardar.emit({ ...d, nombre: d.nombre.trim(), descripcion: d.descripcion.trim(), solucion: d.solucion.trim() });
  }
}
