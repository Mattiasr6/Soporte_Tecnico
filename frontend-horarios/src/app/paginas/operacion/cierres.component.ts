import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ModalComponent } from '../../compartido/modal.component';
import { AuthService } from '../../core/auth.service';
import { EstadoCierre, ReporteTurno } from '../../core/modelos';
import { NotificacionesService } from '../../core/notificaciones.service';
import { NovedadesService } from '../../core/novedades.service';
import { CierresListaComponent, DecisionCierre } from './cierres-lista.component';

const PESTANAS: { valor: EstadoCierre; texto: string }[] = [
  { valor: 'pendiente', texto: 'Pendientes' },
  { valor: 'validado', texto: 'Validados' },
  { valor: 'rechazado', texto: 'Rechazados' },
];

/**
 * Shift-close validation (container), ported from Django's "cierres" tab:
 * Jefe/Encargado validate or reject the closes (`reportes_turno`) that are
 * still pending. Nobody decides on their own close (rule in the API); editing
 * a decided close sends it back to pending.
 */
@Component({
  selector: 'app-cierres',
  imports: [RouterLink, ModalComponent, CierresListaComponent],
  template: `
    <header class="mb-4">
      <h1 class="text-2xl font-bold">Cierres de turno</h1>
      <p class="mt-0.5 text-sm text-slate-600">
        Valida o rechaza los cierres de turno de los auxiliares. Si el autor edita un cierre ya revisado, vuelve a pendiente.
        <a routerLink="/turno" class="text-marca-600 hover:underline">Ver reportes de turno</a>
      </p>
    </header>

    <div class="mb-3 flex rounded-lg bg-slate-100 p-0.5 sm:w-fit">
      @for (p of pestanas; track p.valor) {
        <button type="button" class="flex-1 rounded-md px-3 py-1 text-sm font-medium transition"
                [class]="estado() === p.valor ? 'bg-superficie text-marca-700 shadow-sm' : 'text-slate-500'"
                (click)="cambiarEstado(p.valor)">{{ p.texto }}</button>
      }
    </div>

    <app-cierres-lista [cierres]="cierres()" [fotos]="urls()" [esPropio]="esPropio" [ocupado]="ocupado()"
                       [vacio]="cargando() ? 'Cargando…' : 'No hay cierres en este estado.'"
                       (decidir)="decidir($event)" (verFoto)="fotoGrande.set($event)" />

    <app-modal [abierto]="!!fotoGrande()" [titulo]="fotoGrande()?.titulo ?? ''" ancho="lg" (cerrar)="fotoGrande.set(null)">
      @if (fotoGrande(); as f) {
        <img [src]="f.url" [alt]="f.titulo" class="mx-auto max-h-[70vh] rounded-lg object-contain">
      }
    </app-modal>
  `,
})
export class CierresComponent implements OnInit, OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly servicio = inject(NovedadesService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly pestanas = PESTANAS;
  protected readonly estado = signal<EstadoCierre>('pendiente');
  protected readonly cierres = signal<ReporteTurno[]>([]);
  protected readonly cargando = signal(false);
  protected readonly ocupado = signal<number | null>(null);
  /** Local blob URLs of the key photos (report id -> url) */
  protected readonly urls = signal<Map<number, string>>(new Map());
  protected readonly fotoGrande = signal<{ url: string; titulo: string } | null>(null);
  private pedido = 0;

  protected readonly esPropio = (r: ReporteTurno): boolean => !!r.auxiliar_id && r.auxiliar_id === this.auth.perfil()?.id;

  ngOnInit(): void {
    void this.cargar();
  }

  ngOnDestroy(): void {
    this.liberarFotos();
  }

  protected cambiarEstado(estado: EstadoCierre): void {
    this.estado.set(estado);
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    try {
      const lista = await this.servicio.listarCierres(this.estado());
      if (pedido !== this.pedido) return;
      this.cierres.set(lista);
      void this.descargarFotos(lista, pedido);
    } catch (e) {
      if (pedido === this.pedido) this.notificaciones.error(e, 'No se cargaron los cierres');
    } finally {
      if (pedido === this.pedido) this.cargando.set(false);
    }
  }

  protected async decidir({ reporte, estado }: DecisionCierre): Promise<void> {
    const autor = reporte.autor?.nombre_completo ?? 'sin autor';
    if (estado === 'rechazado' && !confirm(`¿Rechazar el cierre de ${autor}?`)) return;
    this.ocupado.set(reporte.id);
    try {
      await this.servicio.decidirCierre(reporte.id, estado);
      this.notificaciones.exito(estado === 'validado' ? 'Cierre validado' : 'Cierre rechazado');
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se guardó la decisión');
    } finally {
      this.ocupado.set(null);
    }
  }

  private liberarFotos(): void {
    for (const url of this.urls().values()) URL.revokeObjectURL(url);
    this.urls.set(new Map());
  }

  /** Downloads the key photos, three at a time; expired ones are just not shown */
  private async descargarFotos(lista: ReporteTurno[], pedido: number): Promise<void> {
    this.fotoGrande.set(null);
    this.liberarFotos();
    const faltan = lista.filter((r) => r.foto_path).map((r) => r.id);
    const mapa = new Map<number, string>();
    const descargar = async (): Promise<void> => {
      for (let id = faltan.shift(); id !== undefined; id = faltan.shift()) {
        try {
          const url = URL.createObjectURL(await this.servicio.fotoCierre(id));
          if (pedido !== this.pedido) {
            URL.revokeObjectURL(url);
            return;
          }
          mapa.set(id, url);
          this.urls.set(new Map(mapa));
        } catch {
          /* expired or missing photo */
        }
      }
    };
    await Promise.all([descargar(), descargar(), descargar()]);
  }
}
