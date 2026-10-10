import { Component, input, output } from '@angular/core';
import { ItemBorradorSoporte } from '../../core/borrador-soporte.service';
import { AtencionSoporte } from '../../core/soporte.service';

/**
 * Lista del borrador de atenciones y atenciones recientes (presentacional),
 * como el pie de la pantalla "Nueva atención" de Django.
 */
@Component({
  selector: 'app-borrador-soporte-lista',
  template: `
    <section class="tarjeta p-4">
      <h2 class="mb-2 text-lg font-semibold">Lista ({{ items().length }})</h2>
      @for (item of items(); track $index) {
        <div class="flex items-start justify-between gap-2 border-t border-slate-100 py-2 text-sm first:border-t-0"
             [class.bg-amber-50]="editando() === $index">
          <div class="min-w-0">
            <p class="font-medium">{{ item.fecha_registro }} · {{ item.categoria }}</p>
            <p class="truncate text-slate-600" [title]="item.descripcion">{{ recortar(item.descripcion, 60) }}</p>
            <p class="truncate text-xs text-slate-500">{{ item.ruta }}</p>
          </div>
          <div class="flex shrink-0 gap-1">
            <button class="btn-fantasma btn-sm" type="button" title="Editar" (click)="editar.emit($index)">Editar</button>
            <button class="btn-fantasma btn-sm text-red-700" type="button" title="Quitar" [attr.aria-label]="'Quitar la atención ' + ($index + 1)"
                    (click)="quitar.emit($index)">×</button>
          </div>
        </div>
      } @empty {
        <p class="text-sm text-slate-500">Todavía no agregaste ninguna atención.</p>
      }
    </section>

    <section class="tarjeta mt-4 p-4">
      <h2 class="mb-2 text-lg font-semibold">Atenciones recientes</h2>
      @for (a of recientes(); track a.id) {
        <div class="border-t border-slate-100 py-2 text-sm first:border-t-0">
          <p><strong>{{ a.area_solicitante }}</strong> · {{ a.categoria }} · {{ a.fecha_registro }}</p>
          <p class="text-slate-600">{{ recortar(a.descripcion, 80) }}</p>
        </div>
      } @empty {
        <p class="text-sm text-slate-500">Sin recientes.</p>
      }
    </section>
  `,
})
export class BorradorSoporteListaComponent {
  readonly items = input<ItemBorradorSoporte[]>([]);
  readonly editando = input<number | null>(null);
  readonly recientes = input<AtencionSoporte[]>([]);
  readonly editar = output<number>();
  readonly quitar = output<number>();

  /** Django `truncatechars` */
  protected recortar(texto: string, maximo: number): string {
    return texto.length > maximo ? texto.slice(0, maximo - 1) + '…' : texto;
  }
}
