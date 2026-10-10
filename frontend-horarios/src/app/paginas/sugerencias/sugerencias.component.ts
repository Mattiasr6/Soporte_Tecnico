import { Component, inject, OnInit, signal, viewChild } from '@angular/core';
import { NotificacionesService } from '../../core/notificaciones.service';
import { Sugerencia, SugerenciasService } from '../../core/sugerencias.service';
import { SugerenciaFormComponent } from './sugerencia-form.component';
import { SugerenciasListaComponent } from './sugerencias-lista.component';

/**
 * Buzón de sugerencias (Django `sugerencias`), in both menu panels: every
 * logged-in role proposes ideas and sees everyone's, as the backend allows.
 */
@Component({
  selector: 'app-sugerencias',
  imports: [SugerenciaFormComponent, SugerenciasListaComponent],
  template: `
    <header class="mb-4">
      <h1 class="text-2xl font-bold">Buzón de sugerencias</h1>
      <p class="text-sm text-slate-500">Tus ideas para mejorar el sistema. Las ve todo el equipo.</p>
    </header>

    <div class="mb-6 max-w-2xl">
      <app-sugerencia-form [enviando]="enviando()" (enviar)="enviar($event)" />
    </div>

    <h2 class="mb-2 font-semibold">Últimas sugerencias</h2>
    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (error()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudieron cargar las sugerencias: {{ error() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <div class="max-w-2xl"><app-sugerencias-lista [sugerencias]="sugerencias()" /></div>
    }
  `,
})
export class SugerenciasComponent implements OnInit {
  private readonly servicio = inject(SugerenciasService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly formulario = viewChild.required(SugerenciaFormComponent);

  protected readonly sugerencias = signal<Sugerencia[]>([]);
  protected readonly cargando = signal(true);
  protected readonly error = signal('');
  protected readonly enviando = signal(false);

  ngOnInit(): void {
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.error.set('');
    try {
      this.sugerencias.set(await this.servicio.listar());
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }

  protected async enviar(texto: string): Promise<void> {
    this.enviando.set(true);
    try {
      await this.servicio.enviar(texto);
      this.formulario().limpiar();
      this.notificaciones.exito('Sugerencia enviada.');
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo enviar la sugerencia');
    } finally {
      this.enviando.set(false);
    }
  }
}
