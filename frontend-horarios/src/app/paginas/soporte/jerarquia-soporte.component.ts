import { Component, computed, inject, OnInit, signal, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { map } from 'rxjs';
import { normalizar } from '../../compartido/buscador.component';
import { ArbolJerarquiaCompleto, ConteosJerarquia, JerarquiaService } from '../../core/jerarquia.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import { armarRamas, detalleDe, JerarquiaArbolComponent } from './jerarquia-arbol.component';
import { JerarquiaEditorComponent, NuevoNodoJerarquia, RenombreJerarquia } from './jerarquia-editor.component';
import { DestinoSoporte, destinosDeArbol } from './selector-area-soporte.component';

/**
 * Jerarquía de Soporte (container), ported from Django `jerarquia_vista` and
 * `jerarquia_accion_vista`: the sector › dependencia › área catalog with the
 * attention total of every node, and create / rename / move / activate /
 * convert / delete. The selected node lives in the URL (`?nodo=area:12`,
 * `?sueltas=1`) like Django. Jefe or dashboard flag only (backend `is_privileged`).
 */
@Component({
  selector: 'app-jerarquia-soporte',
  imports: [JerarquiaArbolComponent, JerarquiaEditorComponent],
  template: `
    <div class="mb-4">
      <h1 class="text-2xl font-bold">Jerarquía</h1>
      <p class="mt-0.5 text-sm text-slate-600">Sectores, dependencias y áreas del catálogo</p>
    </div>

    @if (cargando() && !arbol()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else if (!arbol()) {
      <div class="tarjeta py-10 text-center text-sm text-slate-500">
        <p>No se pudo cargar la jerarquía.</p>
        <button class="btn-secundario btn-sm mt-3" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" [class.opacity-60]="cargando()">
        <section class="tarjeta p-4">
          <app-jerarquia-arbol [ramas]="ramas()" [seleccion]="clave()" [abierto]="detalle()?.dependencia?.clave ?? null"
                               [soloSueltas]="soloSueltas()" (elegir)="ir($event)" (verSueltas)="verSueltas($event)" />
        </section>
        <section class="tarjeta p-4 lg:self-start">
          <app-jerarquia-editor [detalle]="detalle()" [destinosSector]="destinosSector()" [destinosDependencia]="destinosDependencia()"
                                [ocupado]="ocupado()" (renombrar)="renombrar($event)" (mover)="mover($event)" (alternarActivo)="alternarActivo()"
                                (convertir)="convertir()" (borrar)="borrar()" (crear)="crear($event)" (cerrar)="ir(null)" />
        </section>
      </div>
    }

    <section class="tarjeta mt-4 p-4 text-sm">
      <h2 class="mb-2 font-semibold">Reglas</h2>
      <ul class="list-disc space-y-1 pl-5 text-slate-600">
        <li>Nada con hijos o con atenciones se borra: se <b>desactiva</b>. Un área desactivada deja de ofrecerse al registrar.</li>
        <li>El <b>código</b> no cambia al renombrar: es lo que mantiene válidos los CSV y la historia.</li>
        <li>Mover <b>re-apunta las atenciones</b> del área. Mover una dependencia arrastra sus áreas y re-apunta las de todas.</li>
        <li>Una dependencia tiene que pertenecer al mismo sector que sus áreas.</li>
      </ul>
    </section>
  `,
})
export class JerarquiaSoporteComponent implements OnInit {
  private readonly jerarquia = inject(JerarquiaService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly editor = viewChild(JerarquiaEditorComponent);

  protected readonly arbol = signal<ArbolJerarquiaCompleto | null>(null);
  private readonly conteos = signal<ConteosJerarquia | null>(null);
  protected readonly cargando = signal(false);
  protected readonly ocupado = signal(false);

  private readonly query = toSignal(this.route.queryParamMap.pipe(map((q) => ({ nodo: q.get('nodo'), sueltas: q.get('sueltas') === '1' }))));
  protected readonly clave = computed(() => this.query()?.nodo ?? null);
  protected readonly soloSueltas = computed(() => this.query()?.sueltas ?? false);

  protected readonly ramas = computed(() => armarRamas(this.arbol(), this.conteos()));
  protected readonly detalle = computed(() => detalleDe(this.ramas(), this.clave()));
  protected readonly destinosSector = computed<DestinoSoporte[]>(() =>
    (this.arbol()?.padres ?? []).map((p) => ({ clave: `s${p.id}`, ruta: p.nombre, busca: normalizar(p.nombre), grupo_padre_id: p.id, grupo_id: null, area_id: null })),
  );
  protected readonly destinosDependencia = computed(() => destinosDeArbol(this.arbol()).filter((d) => d.clave.startsWith('g')));

  ngOnInit(): void {
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      const [arbol, conteos] = await Promise.all([this.jerarquia.arbol(), this.jerarquia.conteos()]);
      this.arbol.set(arbol);
      this.conteos.set(conteos);
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo cargar la jerarquía');
    } finally {
      this.cargando.set(false);
    }
  }

  protected ir(clave: string | null): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: { nodo: clave, sueltas: this.soloSueltas() ? 1 : null } });
  }

  protected verSueltas(si: boolean): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: { sueltas: si ? 1 : null, nodo: null } });
  }

  protected renombrar(r: RenombreJerarquia): void {
    const d = this.detalle();
    if (d) void this.ejecutar(() => this.jerarquia.renombrar(d.nodo.tipo, d.nodo.id, r.nombre, r.textoLegado), 'Nombre actualizado.');
  }

  protected mover(destino: DestinoSoporte): void {
    const d = this.detalle();
    if (!d || d.nodo.tipo === 'sector') return;
    const tipo = d.nodo.tipo;
    void this.ejecutar(
      () => this.jerarquia.mover(tipo, d.nodo.id, { grupo_padre_id: destino.grupo_padre_id, grupo_id: destino.grupo_id }),
      'Movido. Las atenciones se re-apuntaron.',
    );
  }

  protected alternarActivo(): void {
    const d = this.detalle();
    if (!d || d.nodo.tipo === 'sector') return;
    const tipo = d.nodo.tipo;
    const activo = !d.nodo.activo;
    void this.ejecutar(() => this.jerarquia.fijarActivo(tipo, d.nodo.id, activo), activo ? 'Activado.' : 'Desactivado.');
  }

  protected convertir(): void {
    const d = this.detalle();
    if (!d || d.nodo.tipo !== 'area') return;
    const aviso = `Se creará la dependencia «${d.nodo.nombre}» en el mismo sector, se moverán sus ${d.nodo.total} atenciones a ella `
      + 'y el área quedará vacía e inactiva. No se puede deshacer.';
    if (!confirm(aviso)) return;
    void this.ejecutar(async () => {
      const r = await this.jerarquia.convertirEnDependencia(d.nodo.id);
      // The área may be gone: show the new dependencia
      this.ir(`dependencia:${r.grupo_id}`);
      return `Dependencia creada con ${r.atenciones_movidas} atenciones. El área quedó inactiva.`;
    });
  }

  protected borrar(): void {
    const d = this.detalle();
    if (!d || !confirm(`¿Eliminar «${d.nodo.nombre}»? No se puede deshacer.`)) return;
    void this.ejecutar(async () => {
      await this.jerarquia.borrar(d.nodo.tipo, d.nodo.id);
      this.ir(null);
      return 'Eliminado.';
    });
  }

  protected crear(n: NuevoNodoJerarquia): void {
    const ubicacion = n.destino ? { grupo_padre_id: n.destino.grupo_padre_id, grupo_id: n.destino.grupo_id } : null;
    void this.ejecutar(async () => {
      await this.jerarquia.crear(n.tipo, n.nombre, ubicacion);
      this.editor()?.limpiarNuevo();
      return 'Creado.';
    });
  }

  /** Runs one action, shows Django's flash text and reloads tree and totals */
  private async ejecutar(accion: () => Promise<unknown>, exito?: string): Promise<void> {
    this.ocupado.set(true);
    try {
      const texto = await accion();
      this.notificaciones.exito(typeof texto === 'string' ? texto : (exito ?? 'Listo.'));
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e);
    } finally {
      this.ocupado.set(false);
    }
  }
}
