import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IconoComponent } from '../../compartido/icono.component';

/** One quick link of the Soporte home */
export interface AccesoSoporte {
  ruta: string;
  texto: string;
  icono: string;
}

/** "Accesos rápidos" of the Soporte home (presentational); the container picks the links per role */
@Component({
  selector: 'app-accesos-soporte',
  imports: [RouterLink, IconoComponent],
  template: `
    <div class="flex flex-wrap gap-2">
      @for (a of accesos(); track a.ruta) {
        <a class="btn-secundario" [routerLink]="a.ruta"><app-icono [nombre]="a.icono" [tamano]="16" /> {{ a.texto }}</a>
      }
    </div>
  `,
})
export class AccesosSoporteComponent {
  readonly accesos = input<AccesoSoporte[]>([]);
}
