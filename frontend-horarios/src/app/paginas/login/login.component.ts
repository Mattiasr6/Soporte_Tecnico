import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IconoComponent } from '../../compartido/icono.component';
import { AuthService } from '../../core/auth.service';

/**
 * Pantalla de inicio de sesión (solo correo y contraseña; sin Google).
 */
@Component({
  selector: 'app-login',
  imports: [FormsModule, IconoComponent],
  template: `
    <div class="flex min-h-full items-center justify-center bg-gradient-to-br from-marca-900 via-marca-700 to-marca-500 p-4">
      <div class="w-full max-w-sm">
        <div class="mb-6 text-center text-white">
          <div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 text-white backdrop-blur"><app-icono nombre="laboratorio" [tamano]="28" /></div>
          <h1 class="text-2xl font-bold">Laboratorios UPDS</h1>
          <p class="text-sm text-white/70">Asignación de laboratorios y ambientes</p>
        </div>

        <div class="tarjeta space-y-4 p-6">
        <form class="space-y-4" (ngSubmit)="ingresar()">
          <div>
            <label class="etiqueta" for="correo">Correo</label>
            <input id="correo" class="campo" type="email" name="correo" [(ngModel)]="correo" required autocomplete="username" maxlength="120">
          </div>
          <div>
            <label class="etiqueta" for="password">Contraseña</label>
            <input id="password" class="campo" type="password" name="password" [(ngModel)]="password" required autocomplete="current-password" maxlength="72">
          </div>
          <button class="btn-primario w-full" type="submit" [disabled]="cargando()">
            {{ cargando() ? 'Ingresando…' : 'Ingresar' }}
          </button>
        </form>
          @if (error()) {
            <p class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{{ error() }}</p>
          }
        </div>
        <p class="mt-4 text-center text-xs text-white/60">Universidad Privada Domingo Savio</p>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected correo = '';
  protected password = '';
  protected readonly cargando = signal(false);
  protected readonly error = signal('');

  /** Valida credenciales y entra al sistema */
  protected async ingresar(): Promise<void> {
    if (!this.correo || !this.password) {
      this.error.set('Ingrese correo y contraseña.');
      return;
    }
    this.cargando.set(true);
    this.error.set('');
    try {
      await this.auth.iniciarSesion(this.correo, this.password);
      await this.router.navigateByUrl(this.auth.esInvitado() ? '/espera' : '/');
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : 'No se pudo iniciar sesión.');
    } finally {
      this.cargando.set(false);
    }
  }
}
