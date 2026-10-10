import { Component, input, linkedSignal, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

/** Up to two time ranges ('HH:MM' or '') */
export interface HorasBloque {
  h1: string;
  f1: string;
  h2: string;
  f2: string;
}

/** One person of a block with the hours stored for it */
export interface FilaHorarioTecnico {
  usuario_id: number;
  nombre: string;
  horas: HorasBloque;
  /** Fixed blocks of the day this person covers (only shown when the table has the column) */
  aporta: string[];
}

export interface PlantillaHorario {
  texto: string;
  horas: HorasBloque;
}

export interface HorasEditadas {
  usuario_id: number;
  horas: HorasBloque;
}

type Campo = keyof HorasBloque;

/**
 * Tabla de un bloque de horarios (presentacional): técnicos lunes a viernes,
 * técnicos sábado o jefes. Cada fila tiene uno o dos turnos, una plantilla que
 * rellena las horas y, si corresponde, lo que aporta a la cobertura y
 * "Limpiar". "Guardar todo" emite todas las filas; la página decide.
 */
@Component({
  selector: 'app-horarios-tecnicos-tabla',
  imports: [FormsModule],
  template: `
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-xs text-slate-500">
          <tr>
            <th class="py-2 pr-3 font-medium">{{ columnaPersona() }}</th>
            <th class="py-2 pr-3 font-medium">{{ turno2() ? 'Turno 1' : 'Turno' }}</th>
            @if (turno2()) { <th class="py-2 pr-3 font-medium">Turno 2 (opcional)</th> }
            <th class="py-2 pr-3 font-medium">Plantilla</th>
            @if (columnaAporta()) { <th class="py-2 pr-3 font-medium">{{ columnaAporta() }}</th> }
            @if (conLimpiar()) { <th class="py-2"></th> }
          </tr>
        </thead>
        <tbody>
          @for (f of filas(); track f.usuario_id; let i = $index) {
            <tr class="border-t border-slate-100">
              <td class="py-1.5 pr-3 whitespace-nowrap">{{ f.nombre }}</td>
              <td class="py-1.5 pr-3">
                <div class="flex gap-1">
                  <input type="time" class="campo !w-28 !py-1" [attr.aria-label]="'Inicio de ' + f.nombre" [id]="idBloque() + '_' + f.usuario_id + '_h1'"
                         [ngModel]="horas()[i].h1" (ngModelChange)="cambiar(i, 'h1', $event)">
                  <input type="time" class="campo !w-28 !py-1" [attr.aria-label]="'Fin de ' + f.nombre" [id]="idBloque() + '_' + f.usuario_id + '_f1'"
                         [ngModel]="horas()[i].f1" (ngModelChange)="cambiar(i, 'f1', $event)">
                </div>
              </td>
              @if (turno2()) {
                <td class="py-1.5 pr-3">
                  <div class="flex gap-1">
                    <input type="time" class="campo !w-28 !py-1" [attr.aria-label]="'Inicio del turno 2 de ' + f.nombre" [id]="idBloque() + '_' + f.usuario_id + '_h2'"
                           [ngModel]="horas()[i].h2" (ngModelChange)="cambiar(i, 'h2', $event)">
                    <input type="time" class="campo !w-28 !py-1" [attr.aria-label]="'Fin del turno 2 de ' + f.nombre" [id]="idBloque() + '_' + f.usuario_id + '_f2'"
                           [ngModel]="horas()[i].f2" (ngModelChange)="cambiar(i, 'f2', $event)">
                  </div>
                </td>
              }
              <td class="py-1.5 pr-3">
                <select class="campo !w-48 !py-1" [attr.aria-label]="'Plantilla de ' + f.nombre" (change)="aplicarPlantilla(i, $event)">
                  <option value="">—</option>
                  @for (p of plantillas(); track p.texto; let j = $index) { <option [value]="j">{{ p.texto }}</option> }
                </select>
              </td>
              @if (columnaAporta()) {
                <td class="py-1.5 pr-3 text-xs text-slate-600">
                  @if (f.aporta.length) { {{ f.aporta.join(' · ') }} } @else { <span class="chip bg-slate-200 text-slate-500">no cubre</span> }
                </td>
              }
              @if (conLimpiar()) {
                <td class="py-1.5 text-right">
                  <button type="button" class="btn-fantasma btn-sm" [disabled]="ocupado()" (click)="limpiar.emit(f.usuario_id)">Limpiar</button>
                </td>
              }
            </tr>
          } @empty {
            <tr><td class="py-3 text-slate-500" colspan="6">No hay personas en este bloque.</td></tr>
          }
        </tbody>
      </table>
    </div>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <button type="button" class="btn-primario btn-sm" [disabled]="ocupado() || !filas().length" (click)="enviar()">Guardar todo</button>
      @if (ayuda()) { <span class="text-xs text-slate-500">{{ ayuda() }}</span> }
    </div>
  `,
})
export class HorariosTecnicosTablaComponent {
  /** Prefix of the input ids (lv, sab, jef), like Django */
  readonly idBloque = input.required<string>();
  readonly columnaPersona = input('Técnico');
  readonly filas = input<FilaHorarioTecnico[]>([]);
  readonly plantillas = input<PlantillaHorario[]>([]);
  /** Whether the optional second range is offered (not on Saturday) */
  readonly turno2 = input(true);
  /** Header of the coverage column; empty hides it (Jefes do not count for coverage) */
  readonly columnaAporta = input('');
  readonly conLimpiar = input(true);
  readonly ayuda = input('');
  readonly ocupado = input(false);

  readonly guardar = output<HorasEditadas[]>();
  readonly limpiar = output<number>();

  /** Edited copy of the hours; resets whenever the page sends new rows */
  protected readonly horas = linkedSignal(() => this.filas().map((f) => ({ ...f.horas })));

  protected cambiar(i: number, campo: Campo, valor: string): void {
    this.horas.update((lista) => lista.map((h, j) => (j === i ? { ...h, [campo]: valor ?? '' } : h)));
  }

  protected aplicarPlantilla(i: number, evento: Event): void {
    const select = evento.target as HTMLSelectElement;
    const plantilla = this.plantillas()[Number(select.value)];
    if (select.value === '' || !plantilla) return;
    this.horas.update((lista) => lista.map((h, j) => (j === i ? { ...plantilla.horas } : h)));
    // Back to "—": the template is a one-shot fill, as in Django
    select.value = '';
  }

  protected enviar(): void {
    this.guardar.emit(this.filas().map((f, i) => ({ usuario_id: f.usuario_id, horas: { ...this.horas()[i] } })));
  }
}
