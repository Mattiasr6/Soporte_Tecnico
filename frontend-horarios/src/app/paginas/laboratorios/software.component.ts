import { Component, computed, inject, input, OnInit, signal } from '@angular/core';
import { IconoComponent } from '../../compartido/icono.component';
import { ModalComponent } from '../../compartido/modal.component';
import { AuthService } from '../../core/auth.service';
import { CatalogosService } from '../../core/catalogos.service';
import { PlantillaAtencion, PlantillaNueva, Software, SoftwareNuevo } from '../../core/modelos';
import { NotificacionesService } from '../../core/notificaciones.service';
import { SoftwareService } from '../../core/software.service';
import { PlantillaFormComponent } from './plantilla-form.component';
import { PlantillasListaComponent } from './plantillas-lista.component';
import { SoftwareCatalogoComponent } from './software-catalogo.component';
import { SoftwareFormComponent } from './software-form.component';
import { CeldaSoftware, SoftwareMatrizComponent } from './software-matriz.component';

/**
 * Software of the labs (container), ported from Django `auxiliares/software/`:
 * the lab x software matrix, the catalogue and the attention templates (which
 * prefill the lab attention form). Everyone with access reads it;
 * the Jefe and the Encargado edit (Django `_gestiona_equipo`, API
 * fn_puede_gestionar_auxiliares). Matrix changes are a local draft saved per
 * lab with "Guardar cambios", which replaces each changed lab's whole list
 * (Django "Guardar en este lab"); leaving a lab with no software asks first.
 */
@Component({
  selector: 'app-software',
  imports: [
    IconoComponent, ModalComponent, PlantillaFormComponent, PlantillasListaComponent, SoftwareCatalogoComponent, SoftwareFormComponent,
    SoftwareMatrizComponent,
  ],
  template: `
    <header class="mb-4">
      <h1 class="text-2xl font-bold">Software de laboratorios</h1>
      <p class="mt-0.5 text-sm text-slate-600">Inventario de programas: licencia, uso y qué laboratorio lo tiene. El estado en cada PC se marca desde el croquis del laboratorio.</p>
    </header>

    <section class="mb-8">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">Programas por laboratorio</h2>
        @if (puedeEditar()) {
          <div class="flex items-center gap-2">
            @if (cambiados().size) {
              <button class="btn-secundario btn-sm" (click)="descartar()">Descartar</button>
            }
            <button class="btn-primario btn-sm" [disabled]="!cambiados().size || guardando()" (click)="guardarMatriz()">
              <app-icono nombre="check" [tamano]="15" /> {{ guardando() ? 'Guardando…' : 'Guardar cambios' + (cambiados().size ? ' (' + cambiados().size + ')' : '') }}
            </button>
          </div>
        }
      </div>
      <label class="mb-2 flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" [checked]="verInactivos()" (change)="verInactivos.set(!verInactivos())"> Mostrar programas inactivos
      </label>
      <app-software-matriz [software]="filasMatriz()" [laboratorios]="catalogos.laboratorios()" [instalado]="borrador()"
                           [cambiados]="cambiados()" [resaltado]="labId()" [puedeEditar]="puedeEditar()"
                           (alternar)="alternar($event)" />
    </section>

    <section>
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">Catálogo <span class="font-normal text-slate-400">({{ software().length }})</span></h2>
        @if (puedeEditar()) {
          <button class="btn-primario btn-sm" (click)="abrirForm(null)"><app-icono nombre="agregar" [tamano]="15" /> Agregar programa</button>
        }
      </div>
      <app-software-catalogo [software]="software()" [puedeEditar]="puedeEditar()"
                             [vacio]="cargando() ? 'Cargando…' : 'Catálogo vacío.'"
                             (editar)="abrirForm($event)" (eliminar)="eliminar($event)" />
    </section>

    <section class="mt-8">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Plantillas de atención</h2>
          <p class="text-sm text-slate-500">Textos armados que rellenan el formulario de una atención nueva (tipo, descripción, solución y turno).</p>
        </div>
        @if (puedeEditar()) {
          <button class="btn-primario btn-sm" (click)="formPlantilla.set({ editando: null })"><app-icono nombre="agregar" [tamano]="15" /> Nueva plantilla</button>
        }
      </div>
      <app-plantillas-lista [plantillas]="plantillas()" [puedeEditar]="puedeEditar()"
                            (editar)="formPlantilla.set({ editando: $event })" (eliminar)="eliminarPlantilla($event)" />
    </section>

    <app-modal [abierto]="!!formPlantilla()" [titulo]="formPlantilla()?.editando ? 'Editar plantilla' : 'Nueva plantilla'" ancho="md" (cerrar)="formPlantilla.set(null)">
      @if (formPlantilla(); as f) {
        <app-plantilla-form idForm="form-plantilla" [inicial]="f.editando" (guardar)="guardarPlantilla($event)" />
      }
      <ng-container pie>
        <button class="btn-secundario" (click)="formPlantilla.set(null)">Cancelar</button>
        <button class="btn-primario" type="submit" form="form-plantilla" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Guardar' }}</button>
      </ng-container>
    </app-modal>

    <app-modal [abierto]="!!formSoftware()" [titulo]="formSoftware()?.editando ? 'Editar programa' : 'Agregar programa'" ancho="md" (cerrar)="formSoftware.set(null)">
      @if (formSoftware(); as f) {
        <app-software-form idForm="form-software" [inicial]="f.editando" (guardar)="guardarSoftware($event)" />
      }
      <ng-container pie>
        <button class="btn-secundario" (click)="formSoftware.set(null)">Cancelar</button>
        <button class="btn-primario" type="submit" form="form-software" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Guardar' }}</button>
      </ng-container>
    </app-modal>
  `,
})
export class SoftwareComponent implements OnInit {
  /** `?lab=<ambiente id>` (from the lab panel), bound by the router */
  readonly lab = input<string>();
  protected readonly labId = computed(() => Number(this.lab()) || null);

  protected readonly auth = inject(AuthService);
  protected readonly catalogos = inject(CatalogosService);
  private readonly servicio = inject(SoftwareService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly puedeEditar = this.auth.puedeGestionarAuxiliares;
  protected readonly software = signal<Software[]>([]);
  protected readonly cargando = signal(false);
  protected readonly guardando = signal(false);
  protected readonly verInactivos = signal(false);
  protected readonly formSoftware = signal<{ editando: Software | null } | null>(null);
  protected readonly plantillas = signal<PlantillaAtencion[]>([]);
  protected readonly formPlantilla = signal<{ editando: PlantillaAtencion | null } | null>(null);
  /** Saved state: lab id -> software ids (from the catalogue) */
  private readonly guardado = computed(() => {
    const mapa = new Map<number, Set<number>>();
    for (const s of this.software()) {
      for (const lab of s.ambientes) mapa.set(lab, new Set([...(mapa.get(lab) ?? []), s.id]));
    }
    return mapa;
  });
  /** Unsaved changes: lab id -> its new full set */
  private readonly cambios = signal(new Map<number, Set<number>>());
  protected readonly borrador = computed(() => new Map([...this.guardado(), ...this.cambios()]));
  protected readonly cambiados = computed(() => new Set(this.cambios().keys()));
  /** Active software, plus inactive ones when asked or still installed somewhere */
  protected readonly filasMatriz = computed(() =>
    this.software().filter((s) => s.activo || this.verInactivos() || s.ambientes.length));

  ngOnInit(): void {
    void this.cargar();
    void this.cargarPlantillas();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      this.software.set(await this.servicio.listar());
    } catch (e) {
      this.notificaciones.error(e, 'No se cargó el software');
    } finally {
      this.cargando.set(false);
    }
  }

  protected alternar({ ambienteId, softwareId }: CeldaSoftware): void {
    const actual = new Set(this.borrador().get(ambienteId) ?? []);
    if (!actual.delete(softwareId)) actual.add(softwareId);
    const original = this.guardado().get(ambienteId) ?? new Set<number>();
    const igual = actual.size === original.size && [...actual].every((id) => original.has(id));
    this.cambios.update((m) => {
      const n = new Map(m);
      if (igual) n.delete(ambienteId);
      else n.set(ambienteId, actual);
      return n;
    });
  }

  protected descartar(): void {
    this.cambios.set(new Map());
  }

  protected async guardarMatriz(): Promise<void> {
    const pendientes = [...this.cambios()];
    const vacios = pendientes.filter(([, set]) => !set.size).map(([id]) => this.catalogos.mapaAmbientes().get(id)?.codigo ?? `#${id}`);
    if (vacios.length && !confirm(`Vas a dejar sin ningún programa: ${vacios.join(', ')}. ¿Seguro?`)) return;
    this.guardando.set(true);
    let guardados = 0;
    try {
      for (const [lab, set] of pendientes) {
        await this.servicio.definirDeLaboratorio(lab, [...set]);
        guardados++;
        this.cambios.update((m) => {
          const n = new Map(m);
          n.delete(lab);
          return n;
        });
      }
      this.notificaciones.exito(guardados === 1 ? 'Laboratorio actualizado' : `${guardados} laboratorios actualizados`);
    } catch (e) {
      this.notificaciones.error(e, 'No se guardaron todos los laboratorios');
    } finally {
      this.guardando.set(false);
      await this.recargarSinPerderBorrador();
    }
  }

  protected abrirForm(s: Software | null): void {
    this.formSoftware.set({ editando: s });
  }

  protected async guardarSoftware(datos: SoftwareNuevo): Promise<void> {
    if (!datos.nombre) {
      this.notificaciones.aviso('Escribe el nombre del programa.');
      return;
    }
    const editando = this.formSoftware()?.editando;
    this.guardando.set(true);
    try {
      if (editando) await this.servicio.editar(editando.id, datos);
      else await this.servicio.crear(datos);
      this.formSoftware.set(null);
      this.notificaciones.exito(editando ? 'Programa actualizado' : 'Programa agregado');
      await this.recargarSinPerderBorrador();
    } catch (e) {
      this.notificaciones.error(e, 'No se guardó el programa');
    } finally {
      this.guardando.set(false);
    }
  }

  protected async eliminar(s: Software): Promise<void> {
    const labs = s.ambientes.length ? `\n\nSe quitará de ${s.ambientes.length} laboratorio(s) y de sus PCs.` : '';
    if (!confirm(`¿Eliminar ${s.nombre} del catálogo?${labs}\nSi solo dejó de usarse, mejor márcalo inactivo.`)) return;
    try {
      await this.servicio.eliminar(s.id);
      this.notificaciones.exito('Programa eliminado');
      this.cambios.update((m) => new Map([...m].map(([lab, set]) => [lab, new Set([...set].filter((id) => id !== s.id))])));
      await this.recargarSinPerderBorrador();
    } catch (e) {
      this.notificaciones.error(e, 'No se eliminó el programa');
    }
  }

  private async cargarPlantillas(): Promise<void> {
    try {
      this.plantillas.set(await this.servicio.plantillas());
    } catch (e) {
      this.notificaciones.error(e, 'No se cargaron las plantillas');
    }
  }

  protected async guardarPlantilla(datos: PlantillaNueva): Promise<void> {
    if (!datos.nombre) {
      this.notificaciones.aviso('Escribe el nombre de la plantilla.');
      return;
    }
    const editando = this.formPlantilla()?.editando;
    this.guardando.set(true);
    try {
      if (editando) await this.servicio.editarPlantilla(editando.id, datos);
      else await this.servicio.crearPlantilla(datos);
      this.formPlantilla.set(null);
      this.notificaciones.exito('Plantilla guardada');
      await this.cargarPlantillas();
    } catch (e) {
      this.notificaciones.error(e, 'No se guardó la plantilla');
    } finally {
      this.guardando.set(false);
    }
  }

  protected async eliminarPlantilla(p: PlantillaAtencion): Promise<void> {
    if (!confirm(`¿Eliminar la plantilla ${p.nombre}?`)) return;
    try {
      await this.servicio.eliminarPlantilla(p.id);
      this.notificaciones.exito('Plantilla eliminada');
      await this.cargarPlantillas();
    } catch (e) {
      this.notificaciones.error(e, 'No se eliminó la plantilla');
    }
  }

  /** Reloads the catalogue and drops draft entries that now equal the saved state */
  private async recargarSinPerderBorrador(): Promise<void> {
    await this.cargar();
    this.cambios.update((m) => {
      const n = new Map<number, Set<number>>();
      for (const [lab, set] of m) {
        const original = this.guardado().get(lab) ?? new Set<number>();
        if (set.size !== original.size || [...set].some((id) => !original.has(id))) n.set(lab, set);
      }
      return n;
    });
  }
}
