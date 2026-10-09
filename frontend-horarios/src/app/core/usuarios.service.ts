import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ROL_DE_ROLE, RolSoporte, UsuarioSistema } from './modelos';

/** Datos de un usuario nuevo */
export interface NuevoUsuario {
  nombre_completo: string;
  correo: string;
  password: string;
  /** A new account always gets access, so never Invitado */
  role: Exclude<RolSoporte, 'Invitado'>;
}

/** Campos editables de un usuario (solo se mandan los que cambian) */
export type CambiosUsuario = Partial<Pick<UsuarioSistema, 'nombre_completo' | 'role' | 'activo' | 'turno_habitual' | 'sabado_rotativo'>>;

/**
 * User management (Jefe only). Users are the Soporte ones and the screen speaks
 * Soporte roles; the API takes the perfiles `rol`, so the role is translated
 * here with ROL_DE_ROLE (the server maps it back with ROL_TO_ROLE). Only the
 * horarios-only data (habitual shift, Saturday rotation) lives in perfiles.
 */
@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly api = inject(ApiService);

  listar(): Promise<UsuarioSistema[]> {
    return this.api.get<UsuarioSistema[]>('/usuarios');
  }

  crear({ role, ...datos }: NuevoUsuario): Promise<UsuarioSistema> {
    return this.api.post<UsuarioSistema>('/usuarios', { ...datos, rol: ROL_DE_ROLE[role] });
  }

  actualizar(id: string, { role, ...cambios }: CambiosUsuario): Promise<UsuarioSistema> {
    return this.api.patch<UsuarioSistema>(`/usuarios/${id}`, role ? { ...cambios, rol: ROL_DE_ROLE[role] } : cambios);
  }

  cambiarPassword(id: string, password: string): Promise<void> {
    return this.api.post<void>(`/usuarios/${id}/password`, { password });
  }
}
