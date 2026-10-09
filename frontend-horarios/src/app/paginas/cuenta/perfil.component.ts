import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth.service';
import { CuentaService, UsuarioCuenta } from '../../core/cuenta.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import { CambioPassword, CambioPasswordComponent } from './cambio-password.component';

/**
 * Perfil del usuario actual: sus datos, la especialidad que se ve en el listado
 * del equipo y el cambio de contraseña. Tras cambiarla, el token anterior deja
 * de valer (el backend sube su versión), así que se vuelve a iniciar sesión.
 */
@Component({
  selector: 'app-perfil',
  imports: [FormsModule, CambioPasswordComponent],
  template: `
    <header class="mb-4">
      <h1 class="text-2xl font-bold">Perfil</h1>
      <p class="text-sm text-slate-500">Tu cuenta</p>
    </header>

    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (errorCarga()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudo cargar tu perfil: {{ errorCarga() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else if (usuario(); as u) {
      <div class="grid gap-4 lg:grid-cols-2">
        <section class="tarjeta space-y-4 p-5">
          <div class="flex items-center gap-3">
            <span class="flex h-12 w-12 items-center justify-center rounded-full bg-marca-100 text-lg font-semibold text-marca-700">{{ inicial() }}</span>
            <div class="min-w-0">
              <p class="truncate font-semibold">{{ u.display_name }}</p>
              <p class="text-xs text-slate-500">{{ u.role }}@if (u.estado_actual) { · {{ u.estado_actual }} }</p>
              <p class="truncate text-xs text-slate-500">{{ auth.perfil()?.correo }}</p>
            </div>
          </div>
          <p class="text-xs text-slate-500">El nombre y el correo los maneja el administrador.</p>

          <form class="space-y-2 border-t border-slate-200 pt-4" (ngSubmit)="guardarEspecialidad()">
            <label class="etiqueta" for="perfil-especialidad">Especialidad</label>
            <input class="campo" id="perfil-especialidad" name="especialidad" maxlength="120" placeholder="Ej: Redes y servidores"
                   [ngModel]="especialidad()" (ngModelChange)="especialidad.set($event)">
            <p class="text-xs text-slate-500">Es la que se ve en el listado del equipo.</p>
            <button class="btn-primario" type="submit" [disabled]="guardandoEspecialidad()">
              {{ guardandoEspecialidad() ? 'Guardando…' : 'Guardar' }}
            </button>
          </form>
        </section>

        <section class="tarjeta p-5">
          <h2 class="mb-3 font-semibold">Contraseña</h2>
          <app-cambio-password [enviando]="cambiandoPassword()" [reinicio]="reinicioPassword()" (cambiar)="cambiarPassword($event)" />
        </section>
      </div>
    }
  `,
})
export class PerfilComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly cuenta = inject(CuentaService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly usuario = signal<UsuarioCuenta | null>(null);
  protected readonly cargando = signal(true);
  protected readonly errorCarga = signal('');
  protected readonly especialidad = signal('');
  protected readonly guardandoEspecialidad = signal(false);
  protected readonly cambiandoPassword = signal(false);
  protected readonly reinicioPassword = signal(0);

  protected readonly inicial = computed(() => (this.usuario()?.display_name ?? '?').slice(0, 1).toUpperCase());

  ngOnInit(): void {
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorCarga.set('');
    try {
      const u = await this.cuenta.miUsuario();
      this.usuario.set(u);
      this.especialidad.set(u.especialidad ?? '');
    } catch (e) {
      this.errorCarga.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
  }

  protected async guardarEspecialidad(): Promise<void> {
    const u = this.usuario();
    if (!u) return;
    this.guardandoEspecialidad.set(true);
    try {
      const valor = this.especialidad().trim() || null;
      await this.cuenta.guardarEspecialidad(u.id, valor);
      this.usuario.set({ ...u, especialidad: valor });
      this.notificaciones.exito('Especialidad guardada.');
    } catch (e) {
      this.notificaciones.error(e, 'No se guardó la especialidad');
    } finally {
      this.guardandoEspecialidad.set(false);
    }
  }

  protected async cambiarPassword(datos: CambioPassword): Promise<void> {
    const correo = this.auth.perfil()?.correo ?? '';
    this.cambiandoPassword.set(true);
    try {
      await this.cuenta.cambiarPassword(datos.actual, datos.nueva);
    } catch (e) {
      this.notificaciones.error(e, 'No se cambió la contraseña');
      this.cambiandoPassword.set(false);
      return;
    }
    // The old JWT is now rejected: get a new one with the new password
    try {
      await this.auth.iniciarSesion(correo, datos.nueva);
      this.reinicioPassword.update((n) => n + 1);
      this.notificaciones.exito('Contraseña cambiada.');
    } catch (e) {
      this.notificaciones.error(e, 'La contraseña se cambió, pero hay que volver a iniciar sesión');
      this.auth.sesionExpirada();
    } finally {
      this.cambiandoPassword.set(false);
    }
  }
}
