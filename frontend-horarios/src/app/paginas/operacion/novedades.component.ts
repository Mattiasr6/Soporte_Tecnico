import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconoComponent } from '../../compartido/icono.component';
import { ModalComponent } from '../../compartido/modal.component';
import { AuthService } from '../../core/auth.service';
import { CatalogosService } from '../../core/catalogos.service';
import { Novedad, TurnoCodigo } from '../../core/modelos';
import { NotificacionesService } from '../../core/notificaciones.service';
import { NovedadesService, NovedadNueva } from '../../core/novedades.service';
import { TURNOS_TICKET } from '../../core/tickets';
import { NovedadesListaComponent } from './novedades-lista.component';
import { NovedadFormComponent } from './novedad-form.component';

/**
 * Lab novedades (container), ported from Django `novedades_vista` (tab
 * "novedades"): notices of the last 3 days, filtered by turno and lab on the
 * API. Operators post them (text, turno, lab, optional photo); the author or a
 * Jefe/Encargado deletes them. Old ones simply stop showing (no purge button).
 */
@Component({
  selector: 'app-novedades',
  imports: [FormsModule, IconoComponent, ModalComponent, NovedadesListaComponent, NovedadFormComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Novedades</h1>
        <p class="mt-0.5 text-sm text-slate-600">Avisos de los turnos en los laboratorios. Se muestran los últimos 3 días.</p>
      </div>
      @if (auth.puedeOperar()) {
        <button class="btn-primario" (click)="formAbierto.set(true)"><app-icono nombre="agregar" [tamano]="16" /> Nueva novedad</button>
      }
    </header>

    <div class="mb-3 flex flex-wrap items-end gap-2">
      <select class="campo !w-40 !py-1.5" [ngModel]="filtroTurno()" (ngModelChange)="filtrarTurno($event)" aria-label="Turno">
        <option [ngValue]="null">Todos los turnos</option>
        @for (t of turnos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }
      </select>
      <select class="campo !w-40 !py-1.5" [ngModel]="filtroLab()" (ngModelChange)="filtrarLab($event)" aria-label="Laboratorio">
        <option [ngValue]="null">Todos los labs</option>
        @for (lab of catalogos.laboratorios(); track lab.id) { <option [ngValue]="lab.id">{{ lab.codigo }}</option> }
      </select>
    </div>

    <app-novedades-lista [novedades]="novedades()" [fotos]="urls()" [puedeBorrar]="puedeBorrar"
                         [vacio]="cargando() ? 'Cargando…' : 'No hay novedades en los últimos 3 días.'"
                         (verFoto)="fotoGrande.set($event)" (eliminar)="eliminar($event)" />

    <app-modal [abierto]="formAbierto()" titulo="Nueva novedad" ancho="md" (cerrar)="formAbierto.set(false)">
      @if (formAbierto()) {
        <app-novedad-form idForm="form-novedad" [laboratorios]="catalogos.laboratorios()" (guardar)="guardar($event)" />
      }
      <ng-container pie>
        <button class="btn-secundario" (click)="formAbierto.set(false)">Cancelar</button>
        <button class="btn-primario" type="submit" form="form-novedad" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Publicar' }}</button>
      </ng-container>
    </app-modal>

    <app-modal [abierto]="!!fotoGrande()" [titulo]="'Foto de la novedad'" ancho="lg" (cerrar)="fotoGrande.set(null)">
      @if (fotoGrande(); as f) {
        <img [src]="f.url" [alt]="f.titulo" class="mx-auto max-h-[70vh] rounded-lg object-contain">
      }
    </app-modal>
  `,
})
export class NovedadesComponent implements OnInit, OnDestroy {
  protected readonly auth = inject(AuthService);
  protected readonly catalogos = inject(CatalogosService);
  private readonly servicio = inject(NovedadesService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly turnos = TURNOS_TICKET;
  protected readonly novedades = signal<Novedad[]>([]);
  protected readonly cargando = signal(false);
  protected readonly guardando = signal(false);
  protected readonly formAbierto = signal(false);
  protected readonly filtroTurno = signal<TurnoCodigo | null>(null);
  protected readonly filtroLab = signal<number | null>(null);
  /** Local blob URLs of the downloaded photos (novedad id -> url) */
  protected readonly urls = signal<Map<number, string>>(new Map());
  protected readonly fotoGrande = signal<{ url: string; titulo: string } | null>(null);
  /** Ignores answers of a previous filter that arrive late */
  private pedido = 0;

  /** Same rule as the API: the author or a Jefe/Encargado */
  protected readonly puedeBorrar = (n: Novedad): boolean =>
    this.auth.puedeGestionarAuxiliares() || (this.auth.puedeOperar() && n.autor_id === this.auth.perfil()?.id);

  ngOnInit(): void {
    void this.cargar();
  }

  ngOnDestroy(): void {
    this.liberarFotos();
  }

  protected filtrarTurno(turno: TurnoCodigo | null): void {
    this.filtroTurno.set(turno);
    void this.cargar();
  }

  protected filtrarLab(lab: number | null): void {
    this.filtroLab.set(lab);
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    try {
      const lista = await this.servicio.listar({ turno: this.filtroTurno(), ambienteId: this.filtroLab() });
      if (pedido !== this.pedido) return;
      this.novedades.set(lista);
      void this.descargarFotos(lista, pedido);
    } catch (e) {
      if (pedido === this.pedido) this.notificaciones.error(e, 'No se cargaron las novedades');
    } finally {
      if (pedido === this.pedido) this.cargando.set(false);
    }
  }

  protected async guardar(nueva: NovedadNueva): Promise<void> {
    if (!nueva.texto) {
      this.notificaciones.aviso('Escribe la novedad.');
      return;
    }
    this.guardando.set(true);
    try {
      await this.servicio.crear(nueva);
      this.formAbierto.set(false);
      this.notificaciones.exito('Novedad publicada');
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se publicó la novedad');
    } finally {
      this.guardando.set(false);
    }
  }

  protected async eliminar(n: Novedad): Promise<void> {
    if (!confirm('¿Eliminar esta novedad?')) return;
    try {
      await this.servicio.eliminar(n.id);
      this.notificaciones.exito('Novedad eliminada');
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se eliminó la novedad');
    }
  }

  private liberarFotos(): void {
    for (const url of this.urls().values()) URL.revokeObjectURL(url);
    this.urls.set(new Map());
  }

  /** Downloads the photos, three at a time; one that fails is just not shown */
  private async descargarFotos(lista: Novedad[], pedido: number): Promise<void> {
    this.fotoGrande.set(null);
    this.liberarFotos();
    const faltan = lista.filter((n) => n.foto_path).map((n) => n.id);
    const mapa = new Map<number, string>();
    const descargar = async (): Promise<void> => {
      for (let id = faltan.shift(); id !== undefined; id = faltan.shift()) {
        try {
          const url = URL.createObjectURL(await this.servicio.fotoNovedad(id));
          if (pedido !== this.pedido) {
            URL.revokeObjectURL(url);
            return;
          }
          mapa.set(id, url);
          this.urls.set(new Map(mapa));
        } catch {
          /* no photo: it is not shown */
        }
      }
    };
    await Promise.all([descargar(), descargar(), descargar()]);
  }
}
