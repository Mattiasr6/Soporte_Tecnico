import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** Response of GET /api/usuarios/me (the Soporte user behind the session) */
export interface UsuarioCuenta {
  id: number;
  display_name: string;
  especialidad: string | null;
  role: string;
  estado_actual: string;
}

/** Minimum password length the backend accepts (`MINIMO_PASSWORD`) */
export const MINIMO_PASSWORD = 8;

/**
 * "Mi cuenta": perfil, especialidad, contraseña y bloc de notas del usuario
 * actual. Usa las rutas generales del backend (`/api/usuarios`, `/api/auth`).
 */
@Injectable({ providedIn: 'root' })
export class CuentaService {
  private readonly api = inject(ApiRaizService);

  miUsuario(): Promise<UsuarioCuenta> {
    return this.api.get<UsuarioCuenta>('/usuarios/me');
  }

  /** The backend only lets the Jefe (or dashboard viewers) change it */
  guardarEspecialidad(usuarioId: number, especialidad: string | null): Promise<void> {
    return this.api.patch<void>(`/usuarios/${usuarioId}/especialidad`, { especialidad });
  }

  /** Bumps the token version on the server: the current JWT stops working */
  cambiarPassword(actual: string, nueva: string): Promise<void> {
    return this.api.post<void>('/auth/password', { actual, nueva });
  }

  async leerNotas(): Promise<string> {
    const datos = await this.api.get<{ contenido: string | null }>('/usuarios/notas');
    return datos.contenido ?? '';
  }

  guardarNotas(contenido: string): Promise<void> {
    return this.api.put<void>('/usuarios/notas', { contenido });
  }
}
