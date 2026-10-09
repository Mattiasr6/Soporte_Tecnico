import { Component, HostListener, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CuentaService } from '../../core/cuenta.service';

/** Save indicator shown next to the title */
type EstadoNotas = 'vacio' | 'guardado' | 'sin-guardar' | 'guardando' | 'error';

/** Pause after the last keystroke before saving */
const ESPERA_MS = 1200;

/**
 * Bloc de notas personal: se guarda solo mientras se escribe (sin botón), al
 * salir del campo y al dejar la pantalla. Solo lo ve su dueño.
 */
@Component({
  selector: 'app-notas',
  imports: [FormsModule],
  template: `
    <header class="mb-4 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Bloc de notas</h1>
        <p class="text-sm text-slate-500">Solo vos lo ves</p>
      </div>
      <span class="rounded-full px-3 py-1 text-xs font-medium"
            [class]="estado() === 'guardado' ? 'bg-green-100 text-green-800' : estado() === 'error' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'">
        {{ textoEstado() }}
      </span>
    </header>

    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (errorCarga()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudieron cargar tus notas: {{ errorCarga() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <textarea class="campo min-h-[24rem] font-mono" rows="20" aria-label="Notas" placeholder="Escribí lo que quieras recordar…"
                [ngModel]="contenido()" (ngModelChange)="escribir($event)" (blur)="guardarYa()"></textarea>
      <p class="mt-2 text-xs text-slate-500">Se guarda solo, mientras escribís. Sin botón de guardar: el indicador de arriba dice el estado.</p>
    }
  `,
})
export class NotasComponent implements OnInit, OnDestroy {
  private readonly cuenta = inject(CuentaService);

  protected readonly contenido = signal('');
  protected readonly estado = signal<EstadoNotas>('vacio');
  protected readonly mensajeError = signal('');
  protected readonly cargando = signal(true);
  protected readonly errorCarga = signal('');

  private espera: ReturnType<typeof setTimeout> | null = null;
  private enviando = false;
  /** A change arrived while a save was in flight: save again when it ends */
  private pendiente = false;

  ngOnInit(): void {
    void this.cargar();
  }

  ngOnDestroy(): void {
    this.guardarSiPendiente();
  }

  /** Leaving the page or closing the tab with unsaved text: try to save it */
  @HostListener('window:beforeunload')
  protected alSalir(): void {
    this.guardarSiPendiente();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorCarga.set('');
    try {
      const texto = await this.cuenta.leerNotas();
      this.contenido.set(texto);
      this.estado.set(texto.trim() ? 'guardado' : 'vacio');
    } catch (e) {
      this.errorCarga.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }

  protected textoEstado(): string {
    switch (this.estado()) {
      case 'vacio': return 'Vacío';
      case 'guardado': return 'Guardado ✓';
      case 'sin-guardar': return 'Sin guardar…';
      case 'guardando': return 'Guardando…';
      case 'error': return this.mensajeError() || 'No se pudo guardar';
    }
  }

  protected escribir(texto: string): void {
    this.contenido.set(texto);
    this.estado.set('sin-guardar');
    this.cancelarEspera();
    this.espera = setTimeout(() => void this.guardar(), ESPERA_MS);
  }

  protected guardarYa(): void {
    this.cancelarEspera();
    void this.guardar();
  }

  private guardarSiPendiente(): void {
    if (!this.espera) return;
    this.cancelarEspera();
    void this.guardar();
  }

  private cancelarEspera(): void {
    if (this.espera) clearTimeout(this.espera);
    this.espera = null;
  }

  private async guardar(): Promise<void> {
    if (this.enviando) {
      this.pendiente = true;
      return;
    }
    this.enviando = true;
    this.estado.set('guardando');
    try {
      await this.cuenta.guardarNotas(this.contenido());
      this.estado.set('guardado');
    } catch (e) {
      this.mensajeError.set(e instanceof Error ? e.message : 'No se pudo guardar');
      this.estado.set('error');
    } finally {
      this.enviando = false;
      if (this.pendiente) {
        this.pendiente = false;
        void this.guardar();
      }
    }
  }
}
