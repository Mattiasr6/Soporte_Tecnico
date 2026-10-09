import { Component, input, OnInit, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LicenciaSoftware, Software, SoftwareNuevo } from '../../core/modelos';

export const LICENCIAS: { valor: LicenciaSoftware; texto: string }[] = [
  { valor: 'gratuita', texto: 'Gratuita' },
  { valor: 'mixta', texto: 'Mixta' },
  { valor: 'paga', texto: 'Paga' },
];

/**
 * Software form (presentational), same fields as Django `software.html`:
 * nombre, licencia, uso and the esencial/docentes/activo flags. Submitted by a
 * button outside the form through `idForm` (modal footer).
 */
@Component({
  selector: 'app-software-form',
  imports: [FormsModule],
  template: `
    <form class="grid gap-3 sm:grid-cols-2" [id]="idForm()" (ngSubmit)="enviar()">
      <div class="sm:col-span-2">
        <label class="etiqueta" for="sw-nombre">Nombre *</label>
        <input id="sw-nombre" class="campo" maxlength="150" [(ngModel)]="datos.nombre" name="nombre" placeholder="Ej: SPSS 29" required>
      </div>
      <div>
        <label class="etiqueta" for="sw-licencia">Licencia</label>
        <select id="sw-licencia" class="campo" [(ngModel)]="datos.licencia" name="licencia">
          @for (l of licencias; track l.valor) { <option [ngValue]="l.valor">{{ l.texto }}</option> }
        </select>
      </div>
      <div>
        <label class="etiqueta" for="sw-uso">Uso</label>
        <input id="sw-uso" class="campo" maxlength="250" [(ngModel)]="datos.uso" name="uso" placeholder="Ej: estadística">
      </div>
      <div class="flex flex-wrap gap-4 text-sm sm:col-span-2">
        <label class="flex items-center gap-2"><input type="checkbox" [(ngModel)]="datos.esencial" name="esencial"> Esencial (debe estar en todos los labs)</label>
        <label class="flex items-center gap-2"><input type="checkbox" [(ngModel)]="datos.docentes" name="docentes"> Lo usan docentes</label>
        <label class="flex items-center gap-2"><input type="checkbox" [(ngModel)]="datos.activo" name="activo"> Activo</label>
      </div>
    </form>
  `,
})
export class SoftwareFormComponent implements OnInit {
  readonly idForm = input.required<string>();
  /** Software to edit; null for a new one */
  readonly inicial = input<Software | null>(null);
  readonly guardar = output<SoftwareNuevo>();

  protected readonly licencias = LICENCIAS;
  protected datos: SoftwareNuevo = { nombre: '', licencia: 'gratuita', uso: '', esencial: false, docentes: false, activo: true };

  ngOnInit(): void {
    const s = this.inicial();
    if (s) {
      this.datos = { nombre: s.nombre, licencia: s.licencia, uso: s.uso, esencial: s.esencial, docentes: s.docentes, activo: s.activo };
    }
  }

  protected enviar(): void {
    this.guardar.emit({ ...this.datos, nombre: this.datos.nombre.trim(), uso: this.datos.uso.trim() });
  }
}
