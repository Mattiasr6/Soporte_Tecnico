import { DatePipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { Atencion, EstadoAtencion } from '../../core/modelos';
import {
  ACCIONES_PROGRAMA, CHECKLIST_PREVENTIVO, DetallesTicket, PEDIDOS_DOCENTE, RESULTADOS_CORRECTIVO, textoDe, TIPOS_PERSONA, TIPOS_TICKET,
} from '../../core/tickets';

const ESTADOS: Record<EstadoAtencion, string> = { pendiente: 'Pendiente', en_proceso: 'En proceso', resuelto: 'Resuelto' };
const PRIORIDADES: Record<number, string> = { 1: 'Alta', 2: 'Media', 3: 'Baja' };

/**
 * Printable ticket of one attention record (presentational), like Django's
 * `_lab_ticket.html`: folio, date, lab, type, who registered it, the texts and
 * the PCs of the batch. The page wraps it in `.zona-impresion` to print it.
 */
@Component({
  selector: 'app-ticket-atencion',
  imports: [DatePipe],
  template: `
    @let a = atencion();
    <article class="text-sm">
      <header class="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-slate-200 pb-2">
        <span class="font-mono text-base font-semibold">#{{ a.id }}</span>
        <span class="text-slate-500">{{ a.creado_en | date: 'dd/MM/yyyy HH:mm' }}</span>
        <span class="chip bg-slate-100 text-slate-700">{{ tipo() }}</span>
        <span class="ml-auto text-xs text-slate-500">Soporte Técnico · UPDS</span>
      </header>
      <p class="mb-3 font-medium text-marca-700">{{ a.ambiente?.codigo || 'Sin laboratorio' }}</p>

      <dl class="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div><dt class="text-xs text-slate-500">Registrada por</dt><dd>{{ a.autor?.nombre_completo || '—' }}</dd></div>
        <div><dt class="text-xs text-slate-500">Colaboradores</dt><dd>{{ colaboradores() || '—' }}</dd></div>
        <div><dt class="text-xs text-slate-500">Estado</dt><dd>{{ estado() }}</dd></div>
        <div><dt class="text-xs text-slate-500">Prioridad</dt><dd>{{ prioridades[a.prioridad] ?? '—' }}</dd></div>
        @if (solicitante()) { <div><dt class="text-xs text-slate-500">Solicitante</dt><dd>{{ solicitante() }}</dd></div> }
        @if (pcs().length) { <div class="col-span-2 sm:col-span-3"><dt class="text-xs text-slate-500">PCs ({{ pcs().length }})</dt><dd class="font-mono">{{ pcs().join(', ') }}</dd></div> }
      </dl>

      <section class="mb-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase">Descripción</h3>
        <p class="whitespace-pre-line">{{ a.descripcion }}</p>
      </section>
      @if (detalle()) {
        <section class="mb-3">
          <h3 class="text-xs font-semibold text-slate-500 uppercase">Detalle</h3>
          <p>{{ detalle() }}</p>
        </section>
      }
      <section class="mb-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase">Solución</h3>
        <p class="whitespace-pre-line">{{ a.solucion || '—' }}</p>
      </section>
    </article>
  `,
})
export class TicketAtencionComponent {
  /** First ticket of the record: it carries the shared data */
  readonly atencion = input.required<Atencion>();
  /** Every ticket of the batch (one per PC); empty means a single ticket */
  readonly tickets = input<Atencion[]>([]);
  /** Collaborator names already resolved by the page */
  readonly colaboradores = input('');

  protected readonly prioridades = PRIORIDADES;
  protected readonly tipo = computed(() => TIPOS_TICKET[this.atencion().tipo]?.texto ?? this.atencion().tipo);

  /** Batch state: resolved only when every ticket is */
  protected readonly estado = computed(() => {
    const lista = this.tickets().length ? this.tickets() : [this.atencion()];
    const resueltos = lista.filter((t) => t.estado === 'resuelto').length;
    if (resueltos === lista.length) return ESTADOS.resuelto;
    const base = lista.some((t) => t.estado === 'en_proceso') ? ESTADOS.en_proceso : ESTADOS.pendiente;
    return lista.length > 1 ? `${base} (${resueltos}/${lista.length})` : base;
  });

  protected readonly pcs = computed(() =>
    (this.tickets().length ? this.tickets() : [this.atencion()]).map((t) => t.pc?.etiqueta).filter((e): e is string => !!e));

  protected readonly solicitante = computed(() => {
    const a = this.atencion();
    const d = (a.detalles ?? {}) as DetallesTicket;
    if (a.docente) return `${a.docente.apellidos} ${a.docente.nombres}`;
    return d.persona || a.solicitante || '';
  });

  /** The type-specific data (pedido, programas, checklist, diagnosis…) in one line */
  protected readonly detalle = computed(() => {
    const d = (this.atencion().detalles ?? {}) as DetallesTicket;
    return [
      textoDe(PEDIDOS_DOCENTE, d.pedido), textoDe(ACCIONES_PROGRAMA, d.accion), d.programas,
      (d.checklist ?? []).map((c) => textoDe(CHECKLIST_PREVENTIVO, c)).join(', '), d.diagnostico,
      textoDe(RESULTADOS_CORRECTIVO, d.resultado), textoDe(TIPOS_PERSONA, d.tipo_persona), d.facultad,
      this.atencion().pieza ? `Pieza: ${this.atencion().pieza}` : '',
    ].filter(Boolean).join(' · ');
  });
}
