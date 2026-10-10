import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { fechaActual, MESES } from '../../core/fechas';
import {
  AsignacionHorario, CoberturaHorarios, HorariosTecnicosService, HorarioTecnico,
} from '../../core/horarios-tecnicos.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import { SoporteService, UsuarioSoporte } from '../../core/soporte.service';
import { CoberturaTecnicosComponent } from './cobertura-tecnicos.component';
import {
  FilaHorarioTecnico, HorasBloque, HorasEditadas, HorariosTecnicosTablaComponent, PlantillaHorario,
} from './horarios-tecnicos-tabla.component';

const ZONA = 'America/La_Paz';
const LUNES = 1;
const SABADO = 6;
const LABORABLES = [1, 2, 3, 4, 5];

/** The three forms of the Django screen */
type Bloque = 'laborable' | 'sabado' | 'jefes';

const VACIO: HorasBloque = { h1: '', f1: '', h2: '', f2: '' };

const plantilla = (h1: string, f1: string, h2 = '', f2 = ''): PlantillaHorario => ({
  texto: `${h1}-${f1}${h2 ? ` + ${h2}-${f2}` : ''}`,
  horas: { h1, f1, h2, f2 },
});

/** Django `PLANTILLAS` */
const PLANTILLAS: PlantillaHorario[] = [
  plantilla('08:00', '16:00'),
  plantilla('08:00', '12:00', '14:30', '18:30'),
  plantilla('12:00', '20:00'),
  plantilla('07:00', '15:00'),
  plantilla('09:00', '17:00'),
];
const PLANTILLAS_SABADO: PlantillaHorario[] = [
  { texto: '08:00-12:00 (mañana)', horas: { ...VACIO, h1: '08:00', f1: '12:00' } },
  { texto: '14:30-18:30 (tarde)', horas: { ...VACIO, h1: '14:30', f1: '18:30' } },
];

/** Django `_mes_vecino` */
function mesVecino(mes: number, anio: number, delta: number): { mes: number; anio: number } {
  const indice = anio * 12 + (mes - 1) + delta;
  return { mes: (indice % 12) + 1, anio: Math.floor(indice / 12) };
}

function horasDe(fila: HorarioTecnico | undefined): HorasBloque {
  if (!fila) return { ...VACIO };
  const hhmm = (v: string | null) => (v ?? '').slice(0, 5);
  return { h1: hhmm(fila.hora_inicio1), f1: hhmm(fila.hora_fin1), h2: hhmm(fila.hora_inicio2), f2: hhmm(fila.hora_fin2) };
}

/** Django `_franjas_por_tecnico`: name -> fixed blocks it covers */
function franjasPorTecnico(franjas: CoberturaHorarios['laborable'] | undefined): Map<string, string[]> {
  const mapa = new Map<string, string[]>();
  for (const f of franjas ?? []) for (const nombre of f.tecnicos) mapa.set(nombre, [...(mapa.get(nombre) ?? []), f.franja]);
  return mapa;
}

/**
 * Horarios de técnicos (container), ported from Django `horarios_vista` and
 * `horarios/guardar|limpiar|copiar`: the monthly shift of each Soporte Técnico
 * (one block for lunes–viernes, one for Saturday), the Jefes' fixed shift and
 * the month's coverage. Not the auxiliares' horarios-turno. Month in the URL
 * (`?mes=&anio=`). Jefe or dashboard flag only (backend `is_privileged`).
 */
@Component({
  selector: 'app-horarios-tecnicos',
  imports: [HorariosTecnicosTablaComponent, CoberturaTecnicosComponent],
  template: `
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Horarios de técnicos</h1>
        <p class="mt-0.5 text-sm text-slate-600">Los 4 bloques del día son fijos: 08:00-20:00, de lunes a viernes como equipo</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-secundario btn-sm" aria-label="Mes anterior" (click)="irMes(-1)">◀</button>
        <span class="min-w-36 text-center font-semibold">{{ nombreMes() }} {{ periodo().anio }}</span>
        <button class="btn-secundario btn-sm" aria-label="Mes siguiente" (click)="irMes(1)">▶</button>
      </div>
    </div>

    @if (!cargado() && cargando()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else if (!cargado()) {
      <div class="tarjeta py-10 text-center text-sm text-slate-500">
        <p>No se pudieron cargar los horarios.</p>
        <button class="btn-secundario btn-sm mt-3" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <div class="space-y-4" [class.opacity-60]="cargando()">
        <section class="tarjeta p-4">
          <header class="mb-2"><h2 class="font-semibold">Técnicos · lunes a viernes</h2><small class="text-xs text-slate-500">un bloque para los 5 días</small></header>
          <app-horarios-tecnicos-tabla idBloque="lv" [filas]="filasLaborable()" [plantillas]="plantillas" columnaAporta="Aporta" [ocupado]="ocupado()"
                                       ayuda="o usá «Limpiar» para borrar el horario del mes de una persona"
                                       (guardar)="guardar('laborable', $event)" (limpiar)="limpiar('laborable', $event)" />
        </section>

        <section class="tarjeta p-4">
          <header class="mb-2"><h2 class="font-semibold">Técnicos · sábado</h2>
            <small class="text-xs text-slate-500">5 a la mañana (08:00-12:00) y 2 a la tarde (14:30-18:30); la rotación se cambia a mano</small></header>
          <app-horarios-tecnicos-tabla idBloque="sab" [filas]="filasSabado()" [plantillas]="plantillasSabado" [turno2]="false" columnaAporta="Grupo"
                                       [ocupado]="ocupado()" (guardar)="guardar('sabado', $event)" (limpiar)="limpiar('sabado', $event)" />
        </section>

        <section class="tarjeta p-4">
          <header class="mb-2"><h2 class="font-semibold">Jefes · turno fijo</h2></header>
          <app-horarios-tecnicos-tabla idBloque="jef" columnaPersona="Jefe" [filas]="filasJefes()" [plantillas]="plantillas" [conLimpiar]="false"
                                       ayuda="Turno habitual: 08:00-12:00 + 14:30-18:30" [ocupado]="ocupado()" (guardar)="guardar('jefes', $event)" />
        </section>

        <section class="tarjeta p-4">
          <header class="mb-2"><h2 class="font-semibold">Cobertura del mes</h2><small class="text-xs text-slate-500">{{ nombreMes() }} {{ periodo().anio }}</small></header>
          <div class="grid gap-4 md:grid-cols-2">
            <app-cobertura-tecnicos titulo="Lunes a viernes" [franjas]="cobertura()?.laborable ?? []" />
            <app-cobertura-tecnicos titulo="Sábado" [franjas]="cobertura()?.sabado ?? []" />
          </div>
        </section>

        <section class="tarjeta p-4 text-sm">
          <h2 class="mb-2 font-semibold">Reglas</h2>
          <ul class="mb-3 list-disc space-y-1 pl-5 text-slate-600">
            <li>Un día sin turno significa <b>fuera de turno</b> todo el día: por eso el domingo nadie aparece disponible.</li>
            <li>Los <b>jefes</b> tienen horario pero no cuentan para la cobertura.</li>
            <li>El <b>label</b> se genera solo desde las horas: no se escribe a mano.</li>
            <li>Mientras el mes esté vacío, todos figuran <b>fuera de turno</b>. Cargar los turnos arregla eso.</li>
          </ul>
          <div class="flex flex-wrap items-center gap-3">
            <button class="btn-secundario btn-sm" [disabled]="ocupado()" (click)="copiar()">Copiar los horarios del mes anterior</button>
            <span class="text-xs text-slate-500">trae todos los turnos de {{ previo().mes }}/{{ previo().anio }} a este mes</span>
          </div>
        </section>
      </div>
    }
  `,
})
export class HorariosTecnicosComponent {
  private readonly horarios = inject(HorariosTecnicosService);
  private readonly soporte = inject(SoporteService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly plantillas = PLANTILLAS;
  protected readonly plantillasSabado = PLANTILLAS_SABADO;

  protected readonly periodo = signal(this.mesActual());
  protected readonly previo = computed(() => mesVecino(this.periodo().mes, this.periodo().anio, -1));
  protected readonly nombreMes = computed(() => MESES[this.periodo().mes - 1]);

  private readonly filas = signal<HorarioTecnico[]>([]);
  private readonly personas = signal<UsuarioSoporte[]>([]);
  protected readonly cobertura = signal<CoberturaHorarios | null>(null);
  protected readonly cargado = signal(false);
  protected readonly cargando = signal(false);
  protected readonly ocupado = signal(false);
  /** Drops answers of a month the user already left */
  private consulta = 0;

  /** usuario_id -> dia_semana -> stored row */
  private readonly porPersona = computed(() => {
    const mapa = new Map<number, Map<number, HorarioTecnico>>();
    for (const f of this.filas()) {
      if (!mapa.has(f.usuario_id)) mapa.set(f.usuario_id, new Map());
      mapa.get(f.usuario_id)!.set(f.dia_semana, f);
    }
    return mapa;
  });
  private readonly tecnicos = computed(() => this.personas().filter((p) => p.role === 'Tecnico'));
  private readonly jefes = computed(() => this.personas().filter((p) => p.role === 'Jefe'));

  protected readonly filasLaborable = computed(() => this.armar(this.tecnicos(), LUNES, franjasPorTecnico(this.cobertura()?.laborable)));
  protected readonly filasSabado = computed(() => this.armar(this.tecnicos(), SABADO, franjasPorTecnico(this.cobertura()?.sabado)));
  protected readonly filasJefes = computed(() => this.armar(this.jefes(), LUNES, new Map()));

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((q) => {
      const actual = this.mesActual();
      const mes = Number(q.get('mes'));
      const anio = Number(q.get('anio'));
      this.periodo.set({
        mes: Number.isInteger(mes) && mes >= 1 && mes <= 12 ? mes : actual.mes,
        anio: Number.isInteger(anio) && anio > 0 ? anio : actual.anio,
      });
      void this.cargar();
    });
  }

  protected irMes(delta: number): void {
    const p = mesVecino(this.periodo().mes, this.periodo().anio, delta);
    void this.router.navigate([], { relativeTo: this.route, queryParams: { mes: p.mes, anio: p.anio } });
  }

  protected async cargar(): Promise<void> {
    const { mes, anio } = this.periodo();
    const id = ++this.consulta;
    this.cargando.set(true);
    try {
      const [filas, personas, cobertura] = await Promise.all([
        this.horarios.listar(mes, anio), this.soporte.usuarios(), this.horarios.cobertura(mes, anio),
      ]);
      if (id !== this.consulta) return;
      this.filas.set(filas);
      this.personas.set(personas);
      this.cobertura.set(cobertura);
      this.cargado.set(true);
    } catch (e) {
      if (id === this.consulta) this.notificaciones.error(e, 'No se pudieron cargar los horarios');
    } finally {
      if (id === this.consulta) this.cargando.set(false);
    }
  }

  /**
   * Django `horarios_guardar_vista`: a person with hours gets them on every day
   * of the block; a person without hours loses the block (deleted, never saved empty).
   */
  protected guardar(bloque: Bloque, editadas: HorasEditadas[]): void {
    const { mes, anio } = this.periodo();
    const dias = this.diasDe(bloque);
    const asignaciones: AsignacionHorario[] = [];
    const borrar: [number, number][] = [];
    for (const { usuario_id, horas } of editadas) {
      const h = bloque === 'sabado' ? { ...horas, h2: '', f2: '' } : horas;
      if (![h.h1, h.f1, h.h2, h.f2].some((v) => v)) {
        // Only the days that exist: same result as Django's blind DELETE per day
        for (const dia of dias) if (this.porPersona().get(usuario_id)?.has(dia)) borrar.push([usuario_id, dia]);
        continue;
      }
      for (const dia of dias) {
        asignaciones.push({
          usuario_id, dia_semana: dia, mes, anio,
          hora_inicio1: h.h1 || null, hora_fin1: h.f1 || null, hora_inicio2: h.h2 || null, hora_fin2: h.f2 || null,
        });
      }
    }
    void this.ejecutar(async () => {
      for (const [uid, dia] of borrar) await this.horarios.borrarDia(uid, mes, anio, dia);
      if (asignaciones.length) await this.horarios.guardarLote(asignaciones);
      return `Guardados ${asignaciones.length} turnos.`;
    });
  }

  /** Django `horarios_limpiar_vista`: removes the person's block for the month */
  protected limpiar(bloque: Bloque, usuarioId: number): void {
    const nombre = this.personas().find((p) => p.id === usuarioId)?.display_name ?? '';
    const que = bloque === 'sabado' ? 'del sábado' : 'de lunes a viernes';
    if (!confirm(`¿Borrar el horario ${que} de ${nombre} en ${this.nombreMes()}?`)) return;
    const { mes, anio } = this.periodo();
    void this.ejecutar(async () => {
      for (const dia of this.diasDe(bloque)) await this.horarios.borrarDia(usuarioId, mes, anio, dia);
      return 'Horario borrado.';
    });
  }

  /** Django `horarios_copiar_vista`: every row of the previous month, upserted into this one */
  protected copiar(): void {
    const { mes, anio } = this.periodo();
    const previo = this.previo();
    const nombrePrevio = MESES[previo.mes - 1];
    if (!confirm(`¿Copiar los horarios de ${nombrePrevio} a ${this.nombreMes()}? Se reemplazan los turnos de los mismos días.`)) return;
    void this.ejecutar(async () => {
      const filas = await this.horarios.listar(previo.mes, previo.anio);
      if (!filas.length) {
        // A business rule, not a failure: warn without logging an error
        this.notificaciones.aviso(`El mes anterior (${nombrePrevio}) no tiene horarios.`);
        return null;
      }
      await this.horarios.guardarLote(filas.map((f) => ({
        usuario_id: f.usuario_id, dia_semana: f.dia_semana, mes, anio,
        hora_inicio1: f.hora_inicio1, hora_fin1: f.hora_fin1, hora_inicio2: f.hora_inicio2, hora_fin2: f.hora_fin2,
      })));
      return `Copiados ${filas.length} horarios de ${nombrePrevio}.`;
    });
  }

  private diasDe(bloque: Bloque): number[] {
    return bloque === 'sabado' ? [SABADO] : LABORABLES;
  }

  private armar(personas: UsuarioSoporte[], dia: number, aporta: Map<string, string[]>): FilaHorarioTecnico[] {
    return personas.map((p) => ({
      usuario_id: p.id,
      nombre: p.display_name,
      horas: horasDe(this.porPersona().get(p.id)?.get(dia)),
      aporta: aporta.get(p.display_name) ?? [],
    }));
  }

  private mesActual(): { mes: number; anio: number } {
    const [anio, mes] = fechaActual(ZONA).split('-').map(Number);
    return { mes, anio };
  }

  /** Runs one action, shows Django's flash text and reloads the month */
  private async ejecutar(accion: () => Promise<string | null>): Promise<void> {
    this.ocupado.set(true);
    try {
      const texto = await accion();
      if (texto) this.notificaciones.exito(texto);
    } catch (e) {
      this.notificaciones.error(e);
    } finally {
      this.ocupado.set(false);
      await this.cargar();
    }
  }
}
