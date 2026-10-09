import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Perfil, Rol } from './modelos';

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
  activo: boolean;
  turno_habitual: Perfil['turno_habitual'];
  sabado_rotativo: boolean;
}

const KNOWN_ROLES: readonly Rol[] = ['admin', 'auxiliar', 'decano', 'encargado', 'invitado'];

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

  readonly esAdmin = computed(() => this.perfil()?.rol === 'admin');
  readonly esEncargado = computed(() => this.perfil()?.rol === 'encargado');
  readonly esAuxiliar = computed(() => this.perfil()?.rol === 'auxiliar');
  readonly esDecano = computed(() => this.perfil()?.rol === 'decano');
  /** Entró pero aún no tiene rol: solo ve la pantalla de espera */
  readonly esInvitado = computed(() => this.perfil()?.rol === 'invitado');

  /** Edición ACADÉMICA (horarios de clase, cesiones, eventos, catálogos): admin, decano, encargado */
  readonly puedeEditar = computed(() => ['admin', 'decano', 'encargado'].includes(this.perfil()?.rol ?? ''));
  /** OPERACIÓN (turnos, atenciones, inventario de PCs): admin, encargado, auxiliar */
  readonly puedeOperar = computed(() => ['admin', 'encargado', 'auxiliar'].includes(this.perfil()?.rol ?? ''));
  /** Gestión de auxiliares (listado, turnos, rotación): admin, encargado */
  readonly puedeGestionarAuxiliares = computed(() => ['admin', 'encargado'].includes(this.perfil()?.rol ?? ''));

  private inicializacion: Promise<void> | null = null;

  /** Carga la sesión guardada (se llama desde los guards) */
  inicializar(): Promise<void> {
    if (!this.inicializacion) {
      this.inicializacion = (async () => {
        if (this.sesion()) {
          try {
            await this.cargarPerfil();
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
    const rol = KNOWN_ROLES.includes(me.rol as Rol) ? (me.rol as Rol) : 'invitado';
    this.perfil.set({
      id: me.perfil_id,
      nombre_completo: me.nombre_completo,
      correo: me.correo,
      rol,
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
