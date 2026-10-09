import { Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconoComponent } from '../../compartido/icono.component';
import { Perfil, SabadoGuardar, SabadosMes, TurnoSabado } from '../../core/modelos';
import { fechaCorta, hhmm } from '../../core/fechas';

const TURNOS: TurnoSabado[] = ['M', 'MD', 'T'];
const NOMBRE: Record<TurnoSabado, string> = { M: 'Mañana', MD: 'Mediodía', T: 'Tarde' };
const CORTO: Record<TurnoSabado, string> = { M: 'Mñ', MD: 'Md', T: 'Ta' };
const COLOR: Record<TurnoSabado, string> = {
  M: 'bg-amber-100 text-amber-800',
  MD: 'bg-sky-100 text-sky-800',
  T: 'bg-indigo-100 text-indigo-800',
};
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

/** Editable copy of one Saturday */
interface Borrador {
  nota: string;
  /** 'HH:MM' per turno */
  horas: Record<TurnoSabado, { inicio: string; fin: string }>;
  /** perfil id -> turno ('' = libre) */
  asignados: Record<string, TurnoSabado | ''>;
}

interface Persona {
  id: string;
  nombre: string;
}

/**
 * Saturday planner of a month (presentational), like the Django matrix: one
 * row per team member, one column per Saturday, the cell is the turno. Each
 * date can have its own hours per turno and a note. Edits stay local until
 * "Guardar cambios", which emits only the changed dates.
 */
@Component({
  selector: 'app-planificador-sabados',
  imports: [FormsModule, IconoComponent],
  template: `
    <div class="tarjeta mb-3 flex flex-wrap items-center justify-between gap-3 p-3">
      <div class="flex items-center gap-1">
        <button class="btn-fantasma btn-sm" (click)="moverMes(-1)" aria-label="Mes anterior"><app-icono nombre="anterior" [tamano]="16" /></button>
        <span class="min-w-36 text-center font-semibold capitalize">{{ titulo() }}</span>
        <button class="btn-fantasma btn-sm" (click)="moverMes(1)" aria-label="Mes siguiente"><app-icono nombre="siguiente" [tamano]="16" /></button>
      </div>
      <p class="text-xs text-slate-500">Horario normal: {{ leyenda() }}</p>
      <div class="flex flex-wrap gap-2">
        <ng-content />
        <button class="btn-primario" (click)="emitirGuardar()" [disabled]="guardando() || !cambiados().length">
          <app-icono nombre="check" [tamano]="16" /> {{ guardando() ? 'Guardando…' : 'Guardar cambios' + (cambiados().length ? ' (' + cambiados().length + ')' : '') }}
        </button>
      </div>
    </div>

    @if (plan(); as p) {
      <div class="tarjeta mb-3 overflow-x-auto">
        <table class="tabla">
          <thead>
            <tr>
              <th>Auxiliar</th>
              @for (s of p.sabados; track s.fecha) {
                <th class="text-center">
                  <p>sáb {{ corta(s.fecha) }}</p>
                  <div class="mt-1 flex items-center justify-center gap-1">
                    <button class="btn-fantasma btn-sm !px-1" [class.text-marca-700]="detalle() === s.fecha" (click)="alternarDetalle(s.fecha)"
                            [attr.aria-label]="'Horario y nota del ' + corta(s.fecha)" title="Horario y nota">
                      <app-icono nombre="hora" [tamano]="14" />
                    </button>
                    @if (s.planificado) {
                      <button class="btn-fantasma btn-sm !px-1 text-red-600" (click)="limpiar.emit(s.fecha)"
                              [attr.aria-label]="'Limpiar el ' + corta(s.fecha)" title="Limpiar el sábado">
                        <app-icono nombre="eliminar" [tamano]="14" />
                      </button>
                    }
                  </div>
                  @if (horarioPropio(s.fecha)) { <span class="chip mt-1 bg-amber-50 text-[10px] text-amber-700">Horario propio</span> }
                  @if (cambiados().includes(s.fecha)) { <span class="chip mt-1 bg-slate-100 text-[10px] text-slate-600">Sin guardar</span> }
                </th>
              }
              <th class="text-center">Total</th>
            </tr>
          </thead>
          <tbody>
            @for (persona of personas(); track persona.id) {
              <tr>
                <td class="font-medium whitespace-nowrap">{{ persona.nombre }}</td>
                @for (s of p.sabados; track s.fecha) {
                  <td class="text-center">
                    <select class="campo !w-20 !px-1 !py-0.5 text-xs" [class]="colorDe(valor(s.fecha, persona.id))"
                            [ngModel]="valor(s.fecha, persona.id)" (ngModelChange)="asignar(s.fecha, persona.id, $event)"
                            [attr.aria-label]="persona.nombre + ', sábado ' + corta(s.fecha)">
                      <option value="">—</option>
                      @for (t of turnos; track t) { <option [value]="t">{{ corto[t] }}</option> }
                    </select>
                  </td>
                }
                <td class="text-center font-semibold">{{ totales()[persona.id] || 0 }}</td>
              </tr>
            } @empty {
              <tr><td [attr.colspan]="p.sabados.length + 2" class="py-6 text-center text-sm text-slate-500">No hay auxiliares ni encargados activos.</td></tr>
            }
            <tr class="bg-slate-50 text-xs text-slate-600">
              <td>Por turno</td>
              @for (s of p.sabados; track s.fecha) {
                <td class="text-center whitespace-nowrap">
                  @for (t of turnos; track t) { <span class="mr-1">{{ corto[t] }} {{ conteo(s.fecha, t) }}</span> }
                </td>
              }
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>

      @if (detalle(); as fecha) {
        @if (borrador()[fecha]; as b) {
          <div class="tarjeta mb-3 p-3">
            <div class="mb-2 flex items-center justify-between">
              <h3 class="font-semibold">Sábado {{ corta(fecha) }}: horario y nota</h3>
              <button class="btn-fantasma btn-sm" (click)="detalle.set(null)" aria-label="Cerrar"><app-icono nombre="cerrar" [tamano]="16" /></button>
            </div>
            <div class="space-y-2">
              @for (t of turnos; track t) {
                <div class="grid grid-cols-[6rem_1fr_1fr_auto] items-center gap-2">
                  <span class="text-sm font-medium">{{ nombre[t] }}</span>
                  <input type="time" class="campo" [ngModel]="b.horas[t].inicio" (ngModelChange)="cambiarHora(fecha, t, 'inicio', $event)" [attr.aria-label]="'Inicio ' + nombre[t]">
                  <input type="time" class="campo" [ngModel]="b.horas[t].fin" (ngModelChange)="cambiarHora(fecha, t, 'fin', $event)" [attr.aria-label]="'Fin ' + nombre[t]">
                  <button class="btn-fantasma btn-sm" [disabled]="!esPropia(fecha, t)" (click)="horaNormal(fecha, t)" title="Usar el horario normal">
                    <app-icono nombre="restaurar" [tamano]="14" />
                  </button>
                </div>
              }
              <div>
                <label class="etiqueta" for="sabado-nota">Nota</label>
                <input id="sabado-nota" class="campo" maxlength="200" placeholder="Opcional" [ngModel]="b.nota" (ngModelChange)="cambiarNota(fecha, $event)">
              </div>
            </div>
            <p class="mt-2 text-xs text-slate-500">Si dejas el horario normal, el sábado sigue los horarios de turno. Un sábado sin auxiliares no se guarda.</p>
          </div>
        }
      }

      @if (sinSabado().length) {
        <p class="text-sm text-slate-600"><span class="font-medium">Sin sábado este mes:</span> {{ sinSabado().join(', ') }}</p>
      }
    } @else {
      <p class="tarjeta py-6 text-center text-sm text-slate-500">Cargando sábados…</p>
    }
  `,
})
export class PlanificadorSabadosComponent {
  readonly plan = input<SabadosMes | null>(null);
  /** Active auxiliares and encargados (one row each) */
  readonly equipo = input<Perfil[]>([]);
  readonly guardando = input(false);

  /** Month step (-1/+1) and how many dates are still unsaved */
  readonly mover = output<{ paso: number; pendientes: number }>();
  readonly guardar = output<SabadoGuardar[]>();
  readonly limpiar = output<string>();

  protected readonly turnos = TURNOS;
  protected readonly nombre = NOMBRE;
  protected readonly corto = CORTO;
  protected readonly corta = fechaCorta;

  /** Saturday whose hours/note panel is open */
  protected readonly detalle = signal<string | null>(null);

  /** Usual hours of each turno ('HH:MM') */
  private readonly base = computed(() => {
    const base: Record<string, { inicio: string; fin: string }> = {};
    for (const h of this.plan()?.horarios ?? []) base[h.turno] = { inicio: hhmm(h.hora_inicio), fin: hhmm(h.hora_fin) };
    return base;
  });

  /** Local copy of every Saturday, reset whenever the page sends a new plan */
  protected readonly borrador = linkedSignal<SabadosMes | null, Record<string, Borrador>>({
    source: this.plan,
    computation: (plan) => {
      const copia: Record<string, Borrador> = {};
      for (const s of plan?.sabados ?? []) {
        const b: Borrador = { nota: s.nota ?? '', horas: {} as Borrador['horas'], asignados: {} };
        for (const t of s.turnos) {
          if (!TURNOS.includes(t.turno as TurnoSabado)) continue;
          const turno = t.turno as TurnoSabado;
          b.horas[turno] = { inicio: hhmm(t.hora_inicio), fin: hhmm(t.hora_fin) };
          for (const a of t.auxiliares) b.asignados[a.id] = turno;
        }
        copia[s.fecha] = b;
      }
      return copia;
    },
  });

  /** Dates edited since the last plan */
  protected readonly cambiados = linkedSignal<SabadosMes | null, string[]>({ source: this.plan, computation: () => [] });

  protected readonly titulo = computed(() => {
    const p = this.plan();
    return p ? `${MESES[p.mes - 1]} ${p.anio}` : '';
  });

  protected readonly leyenda = computed(() =>
    TURNOS.filter((t) => this.base()[t]).map((t) => `${CORTO[t]} ${this.base()[t].inicio}–${this.base()[t].fin}`).join(' · '));

  /** Team rows plus anyone planned who is no longer in the team */
  protected readonly personas = computed<Persona[]>(() => {
    const lista: Persona[] = this.equipo().map((m) => ({ id: m.id, nombre: m.nombre_completo }));
    const vistos = new Set(lista.map((p) => p.id));
    for (const s of this.plan()?.sabados ?? []) {
      for (const t of s.turnos) {
        for (const a of t.auxiliares) {
          if (!vistos.has(a.id)) {
            vistos.add(a.id);
            lista.push({ id: a.id, nombre: a.nombre_completo });
          }
        }
      }
    }
    return lista;
  });

  protected readonly totales = computed(() => {
    const totales: Record<string, number> = {};
    for (const b of Object.values(this.borrador())) {
      for (const [id, turno] of Object.entries(b.asignados)) if (turno) totales[id] = (totales[id] ?? 0) + 1;
    }
    return totales;
  });

  protected readonly sinSabado = computed(() =>
    this.equipo().filter((m) => !this.totales()[m.id]).map((m) => m.nombre_completo));

  protected valor(fecha: string, perfilId: string): TurnoSabado | '' {
    return this.borrador()[fecha]?.asignados[perfilId] ?? '';
  }

  protected colorDe(turno: TurnoSabado | ''): string {
    return turno ? COLOR[turno] : '';
  }

  protected conteo(fecha: string, turno: TurnoSabado): number {
    return Object.values(this.borrador()[fecha]?.asignados ?? {}).filter((t) => t === turno).length;
  }

  protected esPropia(fecha: string, turno: TurnoSabado): boolean {
    const h = this.borrador()[fecha]?.horas[turno];
    const base = this.base()[turno];
    return !!h && !!base && (h.inicio !== base.inicio || h.fin !== base.fin);
  }

  protected horarioPropio(fecha: string): boolean {
    return TURNOS.some((t) => this.esPropia(fecha, t));
  }

  protected alternarDetalle(fecha: string): void {
    this.detalle.update((actual) => (actual === fecha ? null : fecha));
  }

  protected asignar(fecha: string, perfilId: string, turno: TurnoSabado | ''): void {
    this.editar(fecha, (b) => ({ ...b, asignados: { ...b.asignados, [perfilId]: turno } }));
  }

  protected cambiarHora(fecha: string, turno: TurnoSabado, campo: 'inicio' | 'fin', valor: string): void {
    this.editar(fecha, (b) => ({ ...b, horas: { ...b.horas, [turno]: { ...b.horas[turno], [campo]: valor } } }));
  }

  protected horaNormal(fecha: string, turno: TurnoSabado): void {
    const base = this.base()[turno];
    if (base) this.editar(fecha, (b) => ({ ...b, horas: { ...b.horas, [turno]: { ...base } } }));
  }

  protected cambiarNota(fecha: string, nota: string): void {
    this.editar(fecha, (b) => ({ ...b, nota }));
  }

  protected moverMes(paso: number): void {
    this.mover.emit({ paso, pendientes: this.cambiados().length });
  }

  /** Emits the changed dates as whole plans (own hours only where they differ) */
  protected emitirGuardar(): void {
    const planes = this.cambiados().map((fecha): SabadoGuardar => {
      const b = this.borrador()[fecha];
      return {
        fecha,
        nota: b.nota.trim() || null,
        turnos: TURNOS.map((turno) => ({
          turno,
          ...(this.esPropia(fecha, turno) ? { hora_inicio: b.horas[turno].inicio, hora_fin: b.horas[turno].fin } : {}),
          auxiliares: Object.entries(b.asignados).filter(([, t]) => t === turno).map(([id]) => id),
        })),
      };
    });
    this.guardar.emit(planes);
  }

  private editar(fecha: string, cambio: (b: Borrador) => Borrador): void {
    this.borrador.update((todo) => ({ ...todo, [fecha]: cambio(todo[fecha]) }));
    this.cambiados.update((lista) => (lista.includes(fecha) ? lista : [...lista, fecha]));
  }
}
