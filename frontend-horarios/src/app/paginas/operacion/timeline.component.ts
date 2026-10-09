import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { IconoComponent } from '../../compartido/icono.component';
import { ModalComponent } from '../../compartido/modal.component';
import { ApiService } from '../../core/api.service';
import { fechaActual, fechaLarga, sumarDias } from '../../core/fechas';
import { NotificacionesService } from '../../core/notificaciones.service';
import { EventoTimeline, rutaFoto, TimelineVistaComponent } from './timeline-vista.component';

/** What GET /timeline returns */
interface Timeline {
  fecha: string;
  eventos: EventoTimeline[];
}

/**
 * Day timeline (container), ported from Django `lab_timeline_vista`: the
 * attentions, shift reports, done tasks and lost objects (registered and
 * delivered) of one La Paz day, newest first. Unlike Django it can show any
 * day. Photos are downloaded as blobs from the existing photo endpoints (an
 * <img src> cannot send the session token); one that fails is just not shown.
 */
@Component({
  selector: 'app-timeline',
  imports: [FormsModule, RouterLink, IconoComponent, ModalComponent, TimelineVistaComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Actividad del día</h1>
        <p class="mt-0.5 text-sm text-slate-600">
          {{ titulo() }}: atenciones, reportes de turno, tareas hechas y objetos perdidos.
          <a routerLink="/tablero-laboratorios" class="text-marca-600 hover:underline">Ver tablero</a>
        </p>
      </div>
      <div class="flex flex-wrap items-end gap-2">
        <button class="btn-secundario btn-sm" (click)="cambiarFecha(sumarDias(fecha(), -1))" aria-label="Día anterior">
          <app-icono nombre="anterior" [tamano]="14" />
        </button>
        <div>
          <label class="etiqueta" for="fecha-timeline">Fecha</label>
          <input id="fecha-timeline" type="date" class="campo !w-44 !py-1.5" [max]="hoy" [ngModel]="fecha()" (ngModelChange)="cambiarFecha($event)">
        </div>
        <button class="btn-secundario btn-sm" (click)="cambiarFecha(sumarDias(fecha(), 1))" [disabled]="fecha() >= hoy" aria-label="Día siguiente">
          <app-icono nombre="siguiente" [tamano]="14" />
        </button>
        <button class="btn-secundario btn-sm" (click)="cambiarFecha(hoy)" [disabled]="fecha() === hoy">Hoy</button>
      </div>
    </header>

    @if (datos(); as d) {
      <app-timeline-vista [eventos]="d.eventos" [fotos]="urls()" (verFoto)="fotoGrande.set($event)" />
    } @else if (cargando()) {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">Cargando…</p>
    } @else {
      <p class="tarjeta py-10 text-center text-sm text-slate-500">No se pudo cargar la actividad.</p>
    }

    <app-modal [abierto]="!!fotoGrande()" [titulo]="fotoGrande()?.titulo ?? ''" ancho="lg" (cerrar)="fotoGrande.set(null)">
      @if (fotoGrande(); as f) {
        <img [src]="f.url" [alt]="f.titulo" class="mx-auto max-h-[70vh] rounded-lg object-contain">
      }
    </app-modal>
  `,
})
export class TimelineComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly hoy = fechaActual(environment.zonaHoraria);
  protected readonly sumarDias = sumarDias;
  protected readonly fecha = signal(this.hoy);
  protected readonly datos = signal<Timeline | null>(null);
  protected readonly cargando = signal(false);
  /** Local blob URLs of the downloaded photos (API path -> url) */
  protected readonly urls = signal<Map<string, string>>(new Map());
  protected readonly fotoGrande = signal<{ url: string; titulo: string } | null>(null);
  /** Ignores answers of a previous date that arrive late */
  private pedido = 0;

  ngOnInit(): void {
    void this.cargar();
  }

  ngOnDestroy(): void {
    this.liberarFotos();
  }

  protected titulo(): string {
    return this.fecha() === this.hoy ? 'Hoy' : fechaLarga(this.fecha());
  }

  protected cambiarFecha(fecha: string): void {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha ?? '') || fecha > this.hoy) return;
    this.fecha.set(fecha);
    // Its blob URL is released with the previous day's photos
    this.fotoGrande.set(null);
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    try {
      const datos = await this.api.get<Timeline>('/timeline', { fecha: this.fecha() });
      if (pedido !== this.pedido) return;
      this.datos.set(datos);
      void this.descargarFotos(datos.eventos, pedido);
    } catch (e) {
      if (pedido !== this.pedido) return;
      this.datos.set(null);
      this.notificaciones.error(e, 'No se cargó la actividad del día');
    } finally {
      if (pedido === this.pedido) this.cargando.set(false);
    }
  }

  private liberarFotos(): void {
    for (const url of this.urls().values()) URL.revokeObjectURL(url);
    this.urls.set(new Map());
  }

  /** Downloads the day's photos, three at a time */
  private async descargarFotos(eventos: EventoTimeline[], pedido: number): Promise<void> {
    this.liberarFotos();
    const faltan = [...new Set(eventos.map(rutaFoto).filter((r): r is string => !!r))];
    const mapa = new Map<string, string>();
    const descargar = async (): Promise<void> => {
      for (let ruta = faltan.shift(); ruta; ruta = faltan.shift()) {
        try {
          const url = URL.createObjectURL(await this.api.getBlob(ruta));
          if (pedido !== this.pedido) {
            URL.revokeObjectURL(url);
            return;
          }
          mapa.set(ruta, url);
          this.urls.set(new Map(mapa));
        } catch {
          /* no photo: it is not shown */
        }
      }
    };
    await Promise.all([descargar(), descargar(), descargar()]);
  }
}
