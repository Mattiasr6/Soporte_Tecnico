import { Component, computed, input, output } from '@angular/core';
import { AtencionSoporte } from '../../core/soporte.service';

/**
 * Ticket de una atención de Soporte (presentacional): ruta del área, datos y
 * textos. Editar y Eliminar solo aparecen cuando la página dice que es el dueño.
 */
@Component({
  selector: 'app-ticket-soporte',
  template: `
    @let a = atencion();
    <header class="mb-2 flex flex-wrap items-center gap-2 text-sm">
      <span class="font-mono font-semibold">#{{ a.id }}</span>
      <span class="text-slate-500">{{ a.fecha_registro }}</span>
      @if (a.fuera_de_turno) { <span class="chip bg-amber-100 text-amber-800">fuera turno</span> }
    </header>
    <p class="mb-3 text-sm font-medium text-marca-700">{{ ruta() }}</p>
    <dl class="mb-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
      <div><dt class="text-xs text-slate-500">Medio</dt><dd>{{ a.medio_solicitud }}</dd></div>
      <div><dt class="text-xs text-slate-500">Solicitante</dt><dd>{{ a.usuario_solicitante }}</dd></div>
      <div><dt class="text-xs text-slate-500">Categoría</dt><dd>{{ a.categoria }}</dd></div>
      <div><dt class="text-xs text-slate-500">Técnico</dt><dd>{{ a.usuario_nombre }}</dd></div>
      <div><dt class="text-xs text-slate-500">Colaborador</dt><dd>{{ a.colaborador_nombre || '—' }}</dd></div>
    </dl>
    <section class="mb-3">
      <h3 class="text-xs font-semibold text-slate-500 uppercase">Descripción</h3>
      <p class="text-sm whitespace-pre-line">{{ a.descripcion }}</p>
    </section>
    <section class="mb-3">
      <h3 class="text-xs font-semibold text-slate-500 uppercase">Solución</h3>
      <p class="text-sm whitespace-pre-line">{{ a.solucion }}</p>
    </section>
    @if (a.observaciones) {
      <section class="mb-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase">Observaciones</h3>
        <p class="text-sm whitespace-pre-line">{{ a.observaciones }}</p>
      </section>
    }
    @if (a.enlace_apoyo) {
      <section class="mb-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase">Enlace de apoyo</h3>
        <p class="text-sm break-all"><a class="text-marca-700 underline" [href]="a.enlace_apoyo" target="_blank" rel="noopener">{{ a.enlace_apoyo }}</a></p>
      </section>
    }
    @if (puedeEditar()) {
      <footer class="flex gap-2 border-t border-slate-200 pt-3">
        <button class="btn-primario" type="button" (click)="editar.emit()">Editar</button>
        <button class="btn-peligro" type="button" [disabled]="eliminando()" (click)="eliminar.emit()">
          {{ eliminando() ? 'Eliminando…' : 'Eliminar' }}
        </button>
      </footer>
    }
  `,
})
export class TicketSoporteComponent {
  readonly atencion = input.required<AtencionSoporte>();
  /** Only the owner edits or deletes (backend rule) */
  readonly puedeEditar = input(false);
  readonly eliminando = input(false);
  readonly editar = output<void>();
  readonly eliminar = output<void>();

  /** "Sector › Dependencia › Área", like the Django ticket */
  protected readonly ruta = computed(() => {
    const a = this.atencion();
    return [a.grupo_padre_nombre, a.grupo_nombre, a.area_nombre || a.area_solicitante].filter(Boolean).join(' › ');
  });
}
