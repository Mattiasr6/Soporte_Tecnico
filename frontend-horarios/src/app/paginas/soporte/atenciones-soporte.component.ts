import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../compartido/modal.component';
import { AuthService } from '../../core/auth.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import {
  ArbolJerarquia, AtencionSoporte, CambiosAtencionSoporte, CATEGORIAS_SOPORTE, SoporteService, UsuarioSoporte,
} from '../../core/soporte.service';
import { AtencionesSoporteTablaComponent } from './atenciones-soporte-tabla.component';
import { TicketSoporteFormComponent } from './ticket-soporte-form.component';
import { TicketSoporteComponent } from './ticket-soporte.component';

/** Page size and cap of the Django list ("Ver más" adds 50, up to 500) */
const PASO_LISTA = 50;
const MAXIMO_LISTA = 500;

/** Filter values (the technician filter is only for Jefe / dashboard users) */
interface FiltroSoporte {
  q: string;
  categoria: string;
  /** YYYY-MM */
  mes: string;
  tecnico: number | null;
}

const SIN_FILTRO: FiltroSoporte = { q: '', categoria: '', mes: '', tecnico: null };

/** Option of the technician filter */
interface OpcionTecnico {
  id: number;
  nombre: string;
}

/**
 * Atenciones de Soporte (la tabla de Soporte, distinta de las atenciones de
 * laboratorio de /atenciones). Igual que en Django: búsqueda, categoría y mes
 * se filtran en el navegador; el técnico lo filtra el backend. El ticket se
 * abre en una ventana y solo su dueño puede editarlo o eliminarlo.
 */
@Component({
  selector: 'app-atenciones-soporte',
  imports: [FormsModule, ModalComponent, AtencionesSoporteTablaComponent, TicketSoporteComponent, TicketSoporteFormComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Atenciones de Soporte</h1>
        <p class="text-sm text-slate-500">{{ filtradas().length }} registros</p>
      </div>
      <button class="btn-secundario btn-sm" type="button" (click)="limpiar()">Limpiar filtros</button>
    </header>

    <form class="mb-3 flex flex-wrap items-end gap-2" (ngSubmit)="aplicar()">
      <div>
        <label class="etiqueta" for="so-q">Buscar</label>
        <input class="campo !w-56 !py-1.5" id="so-q" name="q" placeholder="Buscar..." [(ngModel)]="borrador.q">
      </div>
      <div>
        <label class="etiqueta" for="so-cat">Categoría</label>
        <select class="campo !w-48 !py-1.5" id="so-cat" name="categoria" [(ngModel)]="borrador.categoria">
          <option value="">Todas las categorías</option>
          @for (c of categorias; track c) { <option [value]="c">{{ c }}</option> }
        </select>
      </div>
      <div>
        <label class="etiqueta" for="so-mes">Mes</label>
        <input class="campo !w-40 !py-1.5" id="so-mes" name="mes" type="month" [(ngModel)]="borrador.mes">
      </div>
      @if (auth.puedeVerDashboard()) {
        <div>
          <label class="etiqueta" for="so-tec">Técnico</label>
          <select class="campo !w-52 !py-1.5" id="so-tec" name="tecnico" [(ngModel)]="borrador.tecnico">
            <option [ngValue]="null">Todos los técnicos</option>
            @for (t of tecnicos(); track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }
          </select>
        </div>
      }
      <button class="btn-primario btn-sm" type="submit">Filtrar</button>
    </form>

    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (error()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudieron cargar las atenciones: {{ error() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <app-atenciones-soporte-tabla [atenciones]="visibles()" (ver)="abrir($event)" />
      <p class="mt-2 text-xs text-slate-500">Mostrando {{ visibles().length }} de {{ filtradas().length }} registros</p>
      @if (restantes() > 0) {
        <p class="mt-2 flex items-center gap-2">
          <button class="btn-secundario btn-sm" type="button" (click)="verMas()">Ver más</button>
          <span class="text-xs text-slate-500">quedan {{ restantes() }}</span>
        </p>
      }
    }

    <app-modal [abierto]="!!abierta()" [titulo]="editando() ? 'Editar atención' : 'Atención #' + (abierta()?.id ?? '')" ancho="lg" (cerrar)="cerrar()">
      @if (abierta(); as a) {
        @if (editando()) {
          @if (arbol()) {
            <app-ticket-soporte-form [atencion]="a" [arbol]="arbol()" [usuarios]="colaboradores()" [guardando]="guardando()"
                                     (guardar)="guardar(a, $event)" (cancelar)="editando.set(false)" />
          } @else {
            <p class="text-sm text-slate-500">Cargando áreas…</p>
          }
        } @else {
          <app-ticket-soporte [atencion]="a" [puedeEditar]="esDueno(a)" [eliminando]="eliminando()"
                              (editar)="editar()" (eliminar)="eliminar(a)" />
        }
      }
    </app-modal>
  `,
})
export class AtencionesSoporteComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly soporte = inject(SoporteService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly categorias = CATEGORIAS_SOPORTE;
  /** Form values; applied on "Filtrar" (Django submits a GET form) */
  protected borrador: FiltroSoporte = { ...SIN_FILTRO };
  private readonly filtro = signal<FiltroSoporte>({ ...SIN_FILTRO });
  private readonly limite = signal(PASO_LISTA);

  protected readonly atenciones = signal<AtencionSoporte[]>([]);
  protected readonly tecnicos = signal<OpcionTecnico[]>([]);
  protected readonly colaboradores = signal<UsuarioSoporte[]>([]);
  protected readonly arbol = signal<ArbolJerarquia | null>(null);
  protected readonly cargando = signal(true);
  protected readonly error = signal('');

  protected readonly abierta = signal<AtencionSoporte | null>(null);
  protected readonly editando = signal(false);
  protected readonly guardando = signal(false);
  protected readonly eliminando = signal(false);

  /** Text search (description or area), category and month, like `lista_vista` */
  protected readonly filtradas = computed(() => {
    const { q, categoria, mes } = this.filtro();
    const texto = q.trim().toLowerCase();
    return this.atenciones().filter(
      (a) =>
        (!texto || a.descripcion.toLowerCase().includes(texto) || a.area_solicitante.toLowerCase().includes(texto)) &&
        (!categoria || a.categoria === categoria) &&
        (!mes || a.fecha_registro.slice(0, 7) === mes),
    );
  });
  protected readonly visibles = computed(() => this.filtradas().slice(0, this.limite()));
  protected readonly restantes = computed(() => (this.limite() >= MAXIMO_LISTA ? 0 : Math.max(this.filtradas().length - this.limite(), 0)));

  ngOnInit(): void {
    void this.cargar();
    if (this.auth.puedeVerDashboard()) void this.cargarTecnicos();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.error.set('');
    try {
      this.atenciones.set(await this.soporte.listarAtenciones(this.filtro().tecnico));
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }

  /** Técnicos and Jefes, including the ones on leave (Django `_tecnicos_para_filtrar`) */
  private async cargarTecnicos(): Promise<void> {
    try {
      const usuarios = await this.soporte.usuarios(true);
      this.tecnicos.set(
        usuarios
          .filter((u) => u.role === 'Tecnico' || u.role === 'Jefe')
          .map((u) => ({ id: u.id, nombre: u.display_name + (u.activo ? '' : ' (de baja)') }))
          .sort((a, b) => a.nombre.localeCompare(b.nombre)),
      );
    } catch (e) {
      this.notificaciones.error(e, 'No se cargó la lista de técnicos');
    }
  }

  protected aplicar(): void {
    const tecnicoCambio = this.borrador.tecnico !== this.filtro().tecnico;
    this.filtro.set({ ...this.borrador });
    this.limite.set(PASO_LISTA);
    if (tecnicoCambio) void this.cargar();
  }

  protected limpiar(): void {
    this.borrador = { ...SIN_FILTRO };
    this.aplicar();
  }

  protected verMas(): void {
    this.limite.update((l) => Math.min(l + PASO_LISTA, MAXIMO_LISTA));
  }

  protected esDueno(a: AtencionSoporte): boolean {
    return a.usuario_id === this.auth.perfil()?.usuario_id;
  }

  protected abrir(a: AtencionSoporte): void {
    this.editando.set(false);
    this.abierta.set(a);
  }

  protected cerrar(): void {
    this.abierta.set(null);
    this.editando.set(false);
  }

  /** The edit form needs the area tree and the collaborators: loaded once, on demand */
  protected async editar(): Promise<void> {
    this.editando.set(true);
    if (this.arbol()) return;
    try {
      const [arbol, usuarios] = await Promise.all([this.soporte.arbol(), this.soporte.usuarios()]);
      this.colaboradores.set(usuarios);
      this.arbol.set(arbol);
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo abrir la edición');
      this.editando.set(false);
    }
  }

  protected async guardar(a: AtencionSoporte, cambios: CambiosAtencionSoporte): Promise<void> {
    this.guardando.set(true);
    try {
      await this.soporte.actualizarAtencion(a.id, cambios);
      this.notificaciones.exito(`Atención #${a.id} actualizada`);
      this.cerrar();
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo guardar');
    } finally {
      this.guardando.set(false);
    }
  }

  protected async eliminar(a: AtencionSoporte): Promise<void> {
    if (!confirm(`¿Eliminar la atención #${a.id}? No se puede deshacer.`)) return;
    this.eliminando.set(true);
    try {
      await this.soporte.eliminarAtencion(a.id);
      this.notificaciones.exito(`Atención #${a.id} eliminada`);
      this.cerrar();
      this.atenciones.update((lista) => lista.filter((x) => x.id !== a.id));
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo eliminar');
    } finally {
      this.eliminando.set(false);
    }
  }
}
