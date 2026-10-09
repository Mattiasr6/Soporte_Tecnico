import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { PlantillaAtencion, TurnoCodigo } from '../../core/modelos';
import { TIPOS_TICKET, TURNOS_TICKET } from '../../core/tickets';

const NOMBRE_TURNO = Object.fromEntries(TURNOS_TICKET.map((t) => [t.valor, t.texto])) as Record<TurnoCodigo, string>;

/** Attention templates list (presentational), like the Django "Plantillas de atención" cards */
@Component({
  selector: 'app-plantillas-lista',
  imports: [IconoComponent],
  template: `
    <div class="grid gap-2 md:grid-cols-2">
      @for (p of plantillas(); track p.id) {
        <article class="tarjeta flex gap-3 p-3" [class.opacity-60]="!p.activa">
          <div class="min-w-0 flex-1">
            <p class="font-semibold">{{ p.nombre }}
              @if (!p.activa) { <span class="chip ml-1 bg-slate-100 text-slate-500">inactiva</span> }
            </p>
            <p class="mt-0.5 text-xs text-slate-500">{{ tipos[p.tipo].texto }}@if (p.turno) { · {{ nombreTurno[p.turno] }} }</p>
            @if (p.descripcion) { <p class="mt-1 text-sm text-slate-700">{{ p.descripcion }}</p> }
            @if (p.solucion) { <p class="mt-0.5 text-sm text-slate-500">→ {{ p.solucion }}</p> }
          </div>
          @if (puedeEditar()) {
            <div class="flex shrink-0 flex-col gap-1">
              <button class="btn-fantasma btn-sm" (click)="editar.emit(p)" title="Editar" aria-label="Editar plantilla"><app-icono nombre="editar" [tamano]="15" /></button>
              <button class="btn-fantasma btn-sm text-red-600" (click)="eliminar.emit(p)" title="Eliminar" aria-label="Eliminar plantilla"><app-icono nombre="eliminar" [tamano]="15" /></button>
            </div>
          }
        </article>
      } @empty {
        <p class="tarjeta py-8 text-center text-sm text-slate-500 md:col-span-2">Sin plantillas todavía.</p>
      }
    </div>
  `,
})
export class PlantillasListaComponent {
  readonly plantillas = input.required<PlantillaAtencion[]>();
  readonly puedeEditar = input(false);
  readonly editar = output<PlantillaAtencion>();
  readonly eliminar = output<PlantillaAtencion>();

  protected readonly tipos = TIPOS_TICKET;
  protected readonly nombreTurno = NOMBRE_TURNO;
}
