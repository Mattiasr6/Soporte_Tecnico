import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { Novedad, TurnoCodigo } from '../../core/modelos';
import { TURNOS_TICKET } from '../../core/tickets';

const NOMBRE_TURNO = Object.fromEntries(TURNOS_TICKET.map((t) => [t.valor, t.texto])) as Record<TurnoCodigo, string>;

/**
 * Novedades wall (presentational), like Django `novedades.html`: one card per
 * novedad with turno, lab, author, time and photo thumbnail. `fotos` maps a
 * novedad id to a local blob URL; `puedeBorrar` says which ones show the
 * delete button (the container applies the role rule).
 */
@Component({
  selector: 'app-novedades-lista',
  imports: [DatePipe, IconoComponent],
  template: `
    <div class="grid gap-3 md:grid-cols-2">
      @for (n of novedades(); track n.id) {
        <article class="tarjeta flex gap-3 p-3" [style.border-left]="'5px solid ' + (n.ambiente?.color || '#94a3b8')">
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-1.5 text-xs">
              <span class="chip bg-marca-50 text-marca-700">Turno {{ nombreTurno[n.turno].toLowerCase() }}</span>
              @if (n.ambiente) {
                <span class="chip bg-slate-100 font-semibold text-slate-700">{{ n.ambiente.codigo }}</span>
              } @else {
                <span class="chip bg-slate-100 text-slate-500">General</span>
              }
              <span class="text-slate-500">{{ n.creado_en | date: 'EEE dd/MM HH:mm' }}</span>
            </p>
            <p class="mt-1.5 text-sm break-words whitespace-pre-line text-slate-800">{{ n.texto }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ n.autor?.nombre_completo || 'Sin autor' }}</p>
          </div>
          <div class="flex shrink-0 flex-col items-end gap-1">
            @if (n.foto_path) {
              @if (fotos().get(n.id); as url) {
                <button type="button" class="h-20 w-20 overflow-hidden rounded-md bg-slate-100" (click)="verFoto.emit({ url, titulo: n.texto })" aria-label="Ver foto">
                  <img [src]="url" alt="Foto de la novedad" class="h-full w-full object-cover" loading="lazy">
                </button>
              } @else {
                <span class="flex h-20 w-20 items-center justify-center rounded-md bg-slate-100 text-slate-400"><app-icono nombre="camara" [tamano]="22" /></span>
              }
            }
            @if (puedeBorrar()(n)) {
              <button class="btn-fantasma btn-sm mt-auto text-red-600" (click)="eliminar.emit(n)" title="Eliminar novedad" aria-label="Eliminar novedad">
                <app-icono nombre="eliminar" [tamano]="15" />
              </button>
            }
          </div>
        </article>
      } @empty {
        <p class="tarjeta py-10 text-center text-sm text-slate-500 md:col-span-2">{{ vacio() }}</p>
      }
    </div>
  `,
})
export class NovedadesListaComponent {
  readonly novedades = input.required<Novedad[]>();
  readonly fotos = input.required<Map<number, string>>();
  readonly puedeBorrar = input.required<(n: Novedad) => boolean>();
  readonly vacio = input('No hay novedades en los últimos 3 días.');
  readonly verFoto = output<{ url: string; titulo: string }>();
  readonly eliminar = output<Novedad>();

  protected readonly nombreTurno = NOMBRE_TURNO;
}
