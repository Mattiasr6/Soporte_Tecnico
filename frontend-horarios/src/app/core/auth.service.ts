import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Perfil, Rol, RolSoporte } from './modelos';

/** localStorage key that holds the JWT issued by the backend */
export const TOKEN_KEY = 'upds.token';

/** Response of POST /api/auth/login */
interface LoginResponse {
  token: string;
  user: { id: number; display_name: string; role: string; email: string };
}

/** Response of GET /api/asignacion/me */
interface MeResponse {
  usuario_id: number;
  perfil_id: string;
  nombre_completo: string;
  correo: string;
  rol: string | null;
  /** Soporte role (Usuarios.Role) */
  role: string;
  /** Usuarios.CanViewDashboard: reports/audit access without the Jefe role */
  can_view_dashboard: boolean;
  activo: boolean;
  turno_habitual: Perfil['turno_habitual'];
  sabado_rotativo: boolean;
}

const KNOWN_ROLS: readonly Rol[] = ['admin', 'auxiliar', 'decano', 'encargado', 'invitado', 'tecnico'];
const KNOWN_ROLES: readonly RolSoporte[] = ['Jefe', 'Encargado', 'Auxiliar', 'Tecnico', 'Decano', 'Invitado'];

/** Reads the stored token; storage may be unavailable (private mode) */
function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the session only lives in memory */
  }
}

/** Extracts the backend error message (`{ detail }`) from an HTTP error */
function backendMessage(error: unknown): string | null {
  if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') return error.error.detail;
  return null;
}

/**
 * Manejo de sesión y rol del usuario actual (JWT del backend FastAPI).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  /** JWT de la sesión (null = sin sesión) */
  readonly sesion = signal<string | null>(readToken());
  /** Perfil del usuario (rol, nombre…) */
  readonly perfil = signal<Perfil | null>(null);
  /** true cuando ya se leyó la sesión guardada */
  readonly listo = signal(false);

  /** Soporte role of the session; missing or unknown counts as Invitado (fail closed) */
  readonly role = computed<RolSoporte>(() => this.perfil()?.role ?? 'Invitado');
  private tieneRol(...roles: RolSoporte[]): boolean {
    return roles.includes(this.role());
  }

  readonly esAdmin = computed(() => this.tieneRol('Jefe'));
  readonly esEncargado = computed(() => this.tieneRol('Encargado'));
  readonly esAuxiliar = computed(() => this.tieneRol('Auxiliar'));
  readonly esTecnico = computed(() => this.tieneRol('Tecnico'));
  readonly esDecano = computed(() => this.tieneRol('Decano'));
  /** Entró pero aún no tiene acceso: solo ve la pantalla de espera */
  readonly esInvitado = computed(() => this.tieneRol('Invitado'));

  /** Edición ACADÉMICA (horarios de clase, cesiones, eventos, catálogos): Jefe, Encargado, Decano */
  readonly puedeEditar = computed(() => this.tieneRol('Jefe', 'Encargado', 'Decano'));
  /** OPERACIÓN (atenciones, estados de PCs, tareas de turno): Jefe, Encargado, Auxiliar, Técnico */
  readonly puedeOperar = computed(() => this.tieneRol('Jefe', 'Encargado', 'Auxiliar', 'Tecnico'));
  /** Gestión de auxiliares (listado, turnos, rotación): Jefe, Encargado */
  readonly puedeGestionarAuxiliares = computed(() => this.tieneRol('Jefe', 'Encargado'));
  /** Reportes y auditoría: Jefe o usuario con dashboard (backend `is_privileged`) */
  readonly puedeVerDashboard = computed(() => this.esAdmin() || this.perfil()?.can_view_dashboard === true);
  /** Atenciones de Soporte: como Django, todos menos Auxiliar y Encargado (el Invitado ni entra) */
  readonly puedeVerSoporte = computed(() => this.tieneRol('Jefe', 'Tecnico', 'Decano'));
  /** Cerrar turno: quien gestiona auxiliares, o el auxiliar en su turno (el técnico no tiene turno) */
  readonly puedeCerrarTurno = computed(() => this.puedeGestionarAuxiliares() || this.esAuxiliar());

  private inicializacion: Promise<void> | null = null;

  /** Carga la sesión guardada (se llama desde los guards) */
  inicializar(): Promise<void> {
    if (!this.inicializacion) {
      this.inicializacion = (async () => {
        if (this.sesion()) {
          try {
            await this.cargarPerfil();
            // A stored token of a user that is no longer active is useless: drop it
            if (!this.perfil()?.activo) this.limpiar();
          } catch {
            this.limpiar();
          }
        }
        this.listo.set(true);
      })();
    }
    return this.inicializacion;
  }

  /** Lee el perfil del usuario autenticado desde el backend */
  private async cargarPerfil(): Promise<void> {
    const me = await firstValueFrom(this.http.get<MeResponse>(`${environment.apiUrl}/asignacion/me`));
    const rol = KNOWN_ROLS.includes(me.rol as Rol) ? (me.rol as Rol) : 'invitado';
    const role = KNOWN_ROLES.includes(me.role as RolSoporte) ? (me.role as RolSoporte) : 'Invitado';
    this.perfil.set({
      id: me.perfil_id,
      usuario_id: me.usuario_id,
      nombre_completo: me.nombre_completo,
      correo: me.correo,
      rol,
      role,
      can_view_dashboard: me.can_view_dashboard === true,
      activo: me.activo,
      turno_habitual: me.turno_habitual,
      sabado_rotativo: me.sabado_rotativo,
    });
  }

  /** Vuelve a leer el perfil (ej. para ver si el admin ya asignó un rol) */
  async recargarPerfil(): Promise<void> {
    if (!this.sesion()) {
      this.perfil.set(null);
      return;
    }
    try {
      await this.cargarPerfil();
    } catch {
      this.perfil.set(null);
    }
  }

  /** Inicia sesión con correo y contraseña */
  async iniciarSesion(correo: string, password: string): Promise<void> {
    let respuesta: LoginResponse;
    try {
      respuesta = await firstValueFrom(
        this.http.post<LoginResponse>(`${environment.apiUrl}/auth/login`, { email: correo.trim(), password }),
      );
    } catch (e) {
      if (e instanceof HttpErrorResponse && (e.status === 401 || e.status === 403)) {
        throw new Error(e.status === 403 ? 'Su usuario no está activo. Solicite al administrador que lo habilite.' : 'Correo o contraseña incorrectos.');
      }
      throw new Error(backendMessage(e) ?? 'No se pudo conectar con el servidor.');
    }
    this.sesion.set(respuesta.token);
    writeToken(respuesta.token);
    try {
      await this.cargarPerfil();
    } catch (e) {
      this.limpiar();
      throw new Error(
        e instanceof HttpErrorResponse && e.status === 403
          ? 'Su usuario no tiene acceso al sistema de laboratorios.'
          : (backendMessage(e) ?? 'No se pudo cargar su perfil.'),
      );
    }
    const perfil = this.perfil();
    if (!perfil || !perfil.activo) {
      await this.cerrarSesion();
      throw new Error('Su usuario no está activo. Solicite al administrador que lo habilite.');
    }
  }

  /** Cierra la sesión (el backend no tiene logout: el JWT solo se descarta) */
  async cerrarSesion(): Promise<void> {
    this.limpiar();
  }

  /** Called by the HTTP interceptor when the API answers 401: drop the session and go to login */
  sesionExpirada(): void {
    if (!this.sesion() && !this.perfil()) return;
    this.limpiar();
    void this.router.navigateByUrl('/login');
  }

  private limpiar(): void {
    writeToken(null);
    this.sesion.set(null);
    this.perfil.set(null);
  }
}
