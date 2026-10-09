import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { normalizar } from '../../compartido/buscador.component';
import { IconoComponent } from '../../compartido/icono.component';
import { ModalComponent } from '../../compartido/modal.component';
import { AuthService } from '../../core/auth.service';
import { Rol, UsuarioSistema } from '../../core/modelos';
import { NotificacionesService } from '../../core/notificaciones.service';
import { CambiosUsuario, UsuariosService } from '../../core/usuarios.service';

/** Formulario de usuario nuevo */
interface FormUsuario {
  nombre: string;
  correo: string;
  password: string;
  rol: Exclude<Rol, 'invitado'>;
}

/**
 * Gestión de usuarios (solo admin): crear, cambiar rol, activar/desactivar
 * y restablecer contraseña. Son los usuarios de Soporte (una sola cuenta para
 * ambos sistemas); el turno habitual es propio de este sistema.
 */
@Component({
  selector: 'app-usuarios',
  imports: [FormsModule, ModalComponent, IconoComponent],
  template: `
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Usuarios</h2>
        <p class="text-sm text-slate-500">Admin: todo · Decano/Encargado: horarios · Encargado/Auxiliar: turnos y atenciones · Auxiliar: solo ve los horarios.</p>
      </div>
      <button class="btn-primario" (click)="nuevo()"><app-icono nombre="agregar" [tamano]="16" /> Nuevo usuario</button>
    </div>

    @if (invitados().length) {
      <div class="tarjeta mb-3 flex flex-wrap items-center gap-2 border-l-4 border-l-amber-400 bg-amber-50/60 p-3 text-sm text-amber-900">
        <app-icono nombre="hora" [tamano]="16" />
        <b>{{ invitados().length }}</b> cuenta(s) sin acceso a este sistema (Invitado o Técnico de Soporte). Para darles acceso, elige su rol en la columna <b>Rol</b>.
        <button class="btn-secundario btn-sm ml-auto" (click)="soloInvitados.set(!soloInvitados())">{{ soloInvitados() ? 'Ver todos' : 'Ver solo esas' }}</button>
      </div>
    }

    <div class="relative mb-3 max-w-sm">
      <app-icono nombre="buscar" [tamano]="16" class="absolute top-1/2 left-3 -translate-y-1/2 text-slate-400" />
      <input class="campo !pl-9" placeholder="Buscar por nombre o correo…" maxlength="60" [ngModel]="busqueda()" (ngModelChange)="busqueda.set($event)">
    </div>

    <div class="tarjeta overflow-x-auto">
      <table class="tabla">
        <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Turno</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          @for (u of filtrados(); track u.id) {
            <tr [class.bg-amber-50]="u.rol === 'invitado'">
              <td class="font-medium">{{ u.nombre_completo }} @if (u.id === auth.perfil()?.id) { <span class="chip bg-marca-50 text-marca-700">usted</span> } @if (u.role === 'Tecnico') { <span class="chip bg-slate-100 text-slate-600">Técnico de Soporte</span> }</td>
              <td>{{ u.correo }}</td>
              <td>
                <select class="campo !w-36 !py-1" [ngModel]="u.rol" (ngModelChange)="actualizar(u, { rol: $event })" [disabled]="u.id === auth.perfil()?.id">
                  @for (r of roles; track r.valor) { <option [value]="r.valor">{{ r.texto }}</option> }
                </select>
              </td>
              <td>
                <select class="campo !w-28 !py-1" [ngModel]="u.turno_habitual ?? ''" (ngModelChange)="actualizar(u, { turno_habitual: $event || null })" [disabled]="u.rol !== 'auxiliar'">
                  @for (t of turnos; track t.valor) { <option [value]="t.valor">{{ t.texto }}</option> }
                </select>
              </td>
              <td>
                <button class="chip cursor-pointer" [class]="u.activo ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'"
                        (click)="actualizar(u, { activo: !u.activo })" [disabled]="u.id === auth.perfil()?.id">
                  {{ u.activo ? 'Activo' : 'Inactivo' }}
                </button>
              </td>
              <td class="text-right"><button class="btn-fantasma btn-sm" (click)="cambiarPassword(u)"><app-icono nombre="clave" [tamano]="15" /> Contraseña</button></td>
            </tr>
          } @empty {
            <tr><td colspan="6" class="py-6 text-center text-sm text-slate-500">Ningún usuario coincide con la búsqueda.</td></tr>
          }
        </tbody>
      </table>
    </div>

    <app-modal [abierto]="!!form()" titulo="Nuevo usuario" (cerrar)="form.set(null)">
      @if (form(); as f) {
        <div class="grid gap-3">
          <div><label class="etiqueta">Nombre completo *</label><input class="campo" [(ngModel)]="f.nombre" maxlength="120"></div>
          <div><label class="etiqueta">Correo *</label><input class="campo" type="email" [(ngModel)]="f.correo" maxlength="120"></div>
          <div><label class="etiqueta">Contraseña * (mínimo 8)</label><input class="campo" type="text" [(ngModel)]="f.password" maxlength="72"></div>
          <div>
            <label class="etiqueta">Rol</label>
            <select class="campo" [(ngModel)]="f.rol">
              @for (r of roles; track r.valor) { @if (r.valor !== 'invitado') { <option [value]="r.valor">{{ r.texto }}</option> } }
            </select>
          </div>
        </div>
      }
      <ng-container pie>
        <button class="btn-secundario" (click)="form.set(null)">Cancelar</button>
        <button class="btn-primario" (click)="crear()" [disabled]="guardando()">{{ guardando() ? 'Creando…' : 'Crear usuario' }}</button>
      </ng-container>
    </app-modal>
  `,
})
export class UsuariosComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly servicio = inject(UsuariosService);
  private readonly notificaciones = inject(NotificacionesService);

  protected readonly usuarios = signal<UsuarioSistema[]>([]);
  protected readonly form = signal<FormUsuario | null>(null);
  protected readonly guardando = signal(false);

  protected readonly busqueda = signal('');
  protected readonly soloInvitados = signal(false);
  /** Cuentas sin acceso a este sistema (Invitado, o Técnico de Soporte) */
  protected readonly invitados = computed(() => this.usuarios().filter((u) => u.rol === 'invitado'));
  /** Invitados primero; filtro por nombre o correo (sin importar tildes) */
  protected readonly filtrados = computed(() => {
    const texto = normalizar(this.busqueda().trim());
    return this.usuarios()
      .filter((u) => !this.soloInvitados() || u.rol === 'invitado')
      .filter((u) => !texto || normalizar(`${u.nombre_completo} ${u.correo}`).includes(texto))
      .sort((a, b) => Number(b.rol === 'invitado') - Number(a.rol === 'invitado'));
  });

  protected readonly roles: { valor: Rol; texto: string }[] = [
    { valor: 'invitado', texto: 'Invitado (sin acceso)' },
    { valor: 'auxiliar', texto: 'Auxiliar' }, { valor: 'encargado', texto: 'Encargado de auxiliares' },
    { valor: 'decano', texto: 'Decano' }, { valor: 'admin', texto: 'Administrador' },
  ];
  protected readonly turnos = [
    { valor: '', texto: '—' }, { valor: 'M', texto: 'Mañana' }, { valor: 'MD', texto: 'Mediodía' },
    { valor: 'T', texto: 'Tarde' }, { valor: 'N', texto: 'Noche' },
  ];

  ngOnInit(): void {
    void this.cargar();
  }

  private async cargar(): Promise<void> {
    try {
      this.usuarios.set(await this.servicio.listar());
    } catch (e) {
      this.notificaciones.error(e);
    }
  }

  protected nuevo(): void {
    this.form.set({ nombre: '', correo: '', password: '', rol: 'auxiliar' });
  }

  /** Crea el usuario en Soporte (puede entrar a ambos sistemas) */
  protected async crear(): Promise<void> {
    const f = this.form();
    if (!f) return;
    if (!f.nombre.trim() || !f.correo.trim() || f.password.length < 8) {
      this.notificaciones.aviso('Complete nombre, correo y una contraseña de al menos 8 caracteres.');
      return;
    }
    this.guardando.set(true);
    try {
      await this.servicio.crear({ nombre_completo: f.nombre.trim(), correo: f.correo.trim(), password: f.password, rol: f.rol });
      this.notificaciones.exito('Usuario creado. Ya puede iniciar sesión.');
      this.form.set(null);
      await this.cargar();
    } catch (e) {
      this.notificaciones.error(e, 'No se creó');
    } finally {
      this.guardando.set(false);
    }
  }

  /**
   * Cambia rol, estado o turno. El rol y el estado son los de Soporte: a un
   * Técnico se le confirma antes, porque deja de ser Técnico en Soporte.
   */
  protected async actualizar(u: UsuarioSistema, cambios: CambiosUsuario): Promise<void> {
    if (cambios.rol && u.role === 'Tecnico'
        && !confirm(`${u.nombre_completo} es Técnico de Soporte. Si cambia su rol aquí, también cambia en Soporte y deja de ser Técnico. ¿Continuar?`)) {
      await this.cargar();
      return;
    }
    try {
      await this.servicio.actualizar(u.id, cambios);
      this.notificaciones.exito('Usuario actualizado.');
    } catch (e) {
      this.notificaciones.error(e);
    }
    await this.cargar();
  }

  protected async cambiarPassword(u: UsuarioSistema): Promise<void> {
    const nueva = prompt(`Nueva contraseña para ${u.correo} (mínimo 8 caracteres):`);
    if (!nueva) return;
    try {
      await this.servicio.cambiarPassword(u.id, nueva);
      this.notificaciones.exito('Contraseña cambiada.');
    } catch (e) {
      this.notificaciones.error(e);
    }
  }
}
