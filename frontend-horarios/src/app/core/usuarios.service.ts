import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Rol, UsuarioSistema } from './modelos';

/** Datos de un usuario nuevo */
export interface NuevoUsuario {
  nombre_completo: string;
  correo: string;
  password: string;
  rol: Exclude<Rol, 'invitado'>;
}

/** Campos editables de un usuario (solo se mandan los que cambian) */
export type CambiosUsuario = Partial<Pick<UsuarioSistema, 'nombre_completo' | 'rol' | 'activo' | 'turno_habitual' | 'sabado_rotativo'>>;

/**
 * Gestión de usuarios (solo admin). Los usuarios son los de Soporte: el servidor
 * traduce el rol de este sistema al rol de Soporte y conserva aquí solo los datos
 * propios de horarios (turno habitual, rotación del sábado).
 */
@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly api = inject(ApiService);

  listar(): Promise<UsuarioSistema[]> {
    return this.api.get<UsuarioSistema[]>('/usuarios');
  }

  crear(datos: NuevoUsuario): Promise<UsuarioSistema> {
    return this.api.post<UsuarioSistema>('/usuarios', datos);
  }

  actualizar(id: string, cambios: CambiosUsuario): Promise<UsuarioSistema> {
    return this.api.patch<UsuarioSistema>(`/usuarios/${id}`, cambios);
  }

  cambiarPassword(id: string, password: string): Promise<void> {
    return this.api.post<void>(`/usuarios/${id}/password`, { password });
  }
}
