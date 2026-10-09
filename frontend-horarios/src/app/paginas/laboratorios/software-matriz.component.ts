import { Component, computed, input, output } from '@angular/core';
import { Ambiente, Software } from '../../core/modelos';

/** One cell of the matrix */
export interface CeldaSoftware {
  ambienteId: number;
  softwareId: number;
}

/**
 * Lab x software matrix (presentational). Django edited one lab at a time
 * ("Programa en un lab"); here every lab is a column and every software a row,
 * and a checkbox says whether that lab has it. `instalado` is the container's
 * draft (lab id -> software ids); `cambiados` marks the labs with unsaved
 * changes. A red count under each lab shows the esencial software it lacks
 * (Django: "los esenciales deben estar en todos los labs").
 */
@Component({
  selector: 'app-software-matriz',
  template: `
    <div class="overflow-x-auto rounded-xl border border-slate-200">
      <table class="text-sm">
        <thead class="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th class="sticky left-0 z-10 min-w-48 bg-slate-50 px-3 py-2 text-left font-semibold">Programa</th>
            @for (lab of laboratorios(); track lab.id) {
              <th class="min-w-16 px-2 py-2 text-center font-semibold"
                  [class]="lab.id === resaltado() ? 'bg-marca-50 text-marca-700' : ''"
                  [style.border-top]="'3px solid ' + lab.color">
                {{ lab.codigo }}
                @if (cambiados().has(lab.id)) { <span class="block text-[10px] font-normal text-amber-700">sin guardar</span> }
              </th>
            }
          </tr>
        </thead>
        <tbody>
          @for (s of software(); track s.id) {
            <tr class="border-t border-slate-100 hover:bg-slate-50/60">
              <th scope="row" class="sticky left-0 z-10 bg-white px-3 py-1.5 text-left font-medium">
                {{ s.nombre }}
                @if (s.esencial) { <span class="chip ml-1 bg-marca-50 text-marca-700">esencial</span> }
                @if (!s.activo) { <span class="chip ml-1 bg-slate-100 text-slate-500">inactivo</span> }
              </th>
              @for (lab of laboratorios(); track lab.id) {
                <td class="px-2 py-1.5 text-center" [class.bg-marca-50]="lab.id === resaltado()">
                  <input type="checkbox" class="h-4 w-4 accent-emerald-600"
                         [checked]="tiene(lab.id, s.id)" [disabled]="!puedeEditar()"
                         [attr.aria-label]="s.nombre + ' en ' + lab.codigo"
                         (change)="alternar.emit({ ambienteId: lab.id, softwareId: s.id })">
                </td>
              }
            </tr>
          } @empty {
            <tr><td class="px-3 py-8 text-center text-slate-500" [attr.colspan]="laboratorios().length + 1">Sin programas en el catálogo.</td></tr>
          }
        </tbody>
        @if (software().length) {
          <tfoot class="border-t border-slate-200 bg-slate-50 text-xs">
            <tr>
              <th class="sticky left-0 z-10 bg-slate-50 px-3 py-1.5 text-left font-semibold text-slate-500">Programas · faltan esenciales</th>
              @for (lab of laboratorios(); track lab.id) {
                <td class="px-2 py-1.5 text-center tabular-nums">
                  {{ instalado().get(lab.id)?.size ?? 0 }}
                  @if (faltanEsenciales().get(lab.id); as n) { <span class="block font-semibold text-red-600" [title]="n + ' esencial(es) sin instalar'">−{{ n }}</span> }
                </td>
              }
            </tr>
          </tfoot>
        }
      </table>
    </div>
  `,
})
export class SoftwareMatrizComponent {
  readonly software = input.required<Software[]>();
  readonly laboratorios = input.required<Ambiente[]>();
  readonly instalado = input.required<Map<number, Set<number>>>();
  readonly cambiados = input<Set<number>>(new Set());
  /** Lab opened from a link (?lab=) */
  readonly resaltado = input<number | null>(null);
  readonly puedeEditar = input(false);
  readonly alternar = output<CeldaSoftware>();

  /** Active esencial software missing in each lab */
  protected readonly faltanEsenciales = computed(() => {
    const esenciales = this.software().filter((s) => s.esencial && s.activo);
    const r = new Map<number, number>();
    for (const lab of this.laboratorios()) {
      const set = this.instalado().get(lab.id);
      const n = esenciales.filter((s) => !set?.has(s.id)).length;
      if (n) r.set(lab.id, n);
    }
    return r;
  });

  protected tiene(ambienteId: number, softwareId: number): boolean {
    return this.instalado().get(ambienteId)?.has(softwareId) ?? false;
  }
}
