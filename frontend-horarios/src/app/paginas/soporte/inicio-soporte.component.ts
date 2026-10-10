import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { AuthService } from '../../core/auth.service';
import { AnuncioEquipo, InicioSoporteService, PresenciaEquipo, UsuarioPresencia } from '../../core/inicio-soporte.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import { AccesoSoporte, AccesosSoporteComponent } from './accesos-soporte.component';
import { AnuncioEquipoComponent } from './anuncio-equipo.component';
import { EquipoPresenciaComponent } from './equipo-presencia.component';
import { MiEstadoSoporteComponent } from './mi-estado-soporte.component';

/** Team and announcement refresh period (Django `inicio.js`: every 20 s) */
const REFRESCO_MS = 20_000;

/**
 * Soporte home (Django `inicio`), for Jefe, Técnico and Decano: my presence
 * state, the team announcement, the team right now and quick links. Only Jefe
 * or dashboard users publish the announcement (the backend enforces it too).
 */
@Component({
  selector: 'app-inicio-soporte',
  imports: [MiEstadoSoporteComponent, AnuncioEquipoComponent, EquipoPresenciaComponent, AccesosSoporteComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Inicio de Soporte</h1>
        <p class="text-sm text-slate-500">Tu equipo ahora y lo que necesitás para el día</p>
      </div>
      <app-mi-estado-soporte [yo]="yo()" [guardando]="cambiandoEstado()" (cambiar)="cambiarEstado($event)" />
    </header>

    @if (error()) {
      <div class="tarjeta mb-4 border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudo cargar el inicio: {{ error() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    }

    <section class="tarjeta mb-4 p-4">
      <header class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="font-semibold">Anuncio del equipo</h2>
        @if (anuncio()?.author) { <small class="text-xs text-slate-500">{{ anuncio()!.author }} · {{ anuncio()!.at }}</small> }
      </header>
      <app-anuncio-equipo [anuncio]="anuncio()" [puedeEditar]="auth.puedeVerDashboard()" [guardando]="publicando()"
                          [aviso]="avisoAnuncio()" [avisoError]="avisoAnuncioError()" (publicar)="publicar($event)" />
    </section>

    <section class="tarjeta mb-4 p-4">
      <header class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="font-semibold">El equipo ahora</h2>
        <small class="text-xs text-slate-500">actualiza cada 20 s</small>
      </header>
      @if (cargando() && !equipo()) {
        <p class="text-sm text-slate-500">Cargando…</p>
      } @else {
        <app-equipo-presencia [presencia]="equipo()" />
      }
    </section>

    <section class="tarjeta p-4">
      <h2 class="mb-2 font-semibold">Accesos rápidos</h2>
      <app-accesos-soporte [accesos]="accesos()" />
    </section>
  `,
})
export class InicioSoporteComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly inicio = inject(InicioSoporteService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly yo = signal<UsuarioPresencia | null>(null);
  protected readonly equipo = signal<PresenciaEquipo | null>(null);
  protected readonly anuncio = signal<AnuncioEquipo | null>(null);
  protected readonly cargando = signal(true);
  protected readonly error = signal('');
  protected readonly cambiandoEstado = signal(false);
  protected readonly publicando = signal(false);
  protected readonly avisoAnuncio = signal('');
  protected readonly avisoAnuncioError = signal(false);

  /** Django quick links; Dashboard, Jerarquía and Horarios only for Jefe or dashboard users (their screens' guard) */
  protected readonly accesos = computed<AccesoSoporte[]>(() => {
    const lista: AccesoSoporte[] = [
      { ruta: '/soporte/atenciones/nueva', texto: 'Registrar atención', icono: 'agregar' },
      { ruta: '/soporte/atenciones', texto: 'Atenciones', icono: 'mantenimiento' },
    ];
    if (this.auth.puedeVerDashboard()) {
      lista.push(
        { ruta: '/soporte/dashboard', texto: 'Dashboard', icono: 'grafico' },
        { ruta: '/soporte/jerarquia', texto: 'Jerarquía', icono: 'capas' },
        { ruta: '/soporte/horarios', texto: 'Horarios', icono: 'hora' },
      );
    }
    return lista;
  });

  ngOnInit(): void {
    void this.cargar();
    const intervalo = setInterval(() => void this.refrescar(), REFRESCO_MS);
    this.destroyRef.onDestroy(() => clearInterval(intervalo));
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.error.set('');
    try {
      const [yo, equipo, anuncio] = await Promise.all([this.inicio.miEstado(), this.inicio.equipo(), this.inicio.anuncio()]);
      this.yo.set(yo);
      this.equipo.set(equipo);
      this.anuncio.set(anuncio);
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }

  /** Silent periodic refresh of the team and the announcement (errors keep the last data, like Django) */
  private async refrescar(): Promise<void> {
    const [equipo, anuncio] = await Promise.allSettled([this.inicio.equipo(), this.inicio.anuncio()]);
    if (equipo.status === 'fulfilled') this.equipo.set(equipo.value);
    if (anuncio.status === 'fulfilled') this.anuncio.set(anuncio.value);
  }

  protected async cambiarEstado(nuevo: 'disponible' | 'ocupado'): Promise<void> {
    this.cambiandoEstado.set(true);
    try {
      await this.inicio.cambiarEstado(nuevo);
      // Re-read me and the team: the backend computes the effective state.
      const [yo, equipo] = await Promise.all([this.inicio.miEstado(), this.inicio.equipo()]);
      this.yo.set(yo);
      this.equipo.set(equipo);
    } catch (e) {
      this.notificaciones.error(e, 'No se pudo cambiar tu estado');
    } finally {
      this.cambiandoEstado.set(false);
    }
  }

  protected async publicar(mensaje: string): Promise<void> {
    this.publicando.set(true);
    this.avisoAnuncio.set('');
    try {
      this.anuncio.set(await this.inicio.publicarAnuncio(mensaje));
      this.avisoAnuncioError.set(false);
      this.avisoAnuncio.set(mensaje ? 'Publicado ✓' : 'Anuncio borrado.');
    } catch (e) {
      this.avisoAnuncioError.set(true);
      this.avisoAnuncio.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.publicando.set(false);
    }
  }
}
