import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** Effective presence state the backend computes (`estado_efectivo`) */
export type EstadoPresencia = 'disponible' | 'ocupado' | 'extraturno' | 'ausente';

/** Display order and priority of the team list (Django `ORDEN_PRESENCIA`) */
export const ORDEN_PRESENCIA: readonly EstadoPresencia[] = ['disponible', 'ocupado', 'extraturno', 'ausente'];

/** Spanish label per state (Django `ETIQUETAS_ESTADO`) */
export const ETIQUETAS_PRESENCIA: Record<EstadoPresencia, string> = {
  disponible: 'Disponible',
  ocupado: 'Ocupado',
  extraturno: 'Fuera de turno',
  ausente: 'Ausente',
};

/** Soporte user with today's presence (GET /api/usuarios and /api/usuarios/me, `UsuarioOut`) */
export interface UsuarioPresencia {
  id: number;
  display_name: string;
  role: string;
  estado_actual: string;
  horario_hoy: string | null;
  entra_a_las: string | null;
  atenciones_hoy: number;
  puede_cambiar_estado: boolean;
}

/** Team announcement (GET/POST /api/announcements); all fields are null when there is none */
export interface AnuncioEquipo {
  message: string | null;
  author: string | null;
  at: string | null;
}

/** Team presence: count per state and the sorted list (Django `_presencia`) */
export interface PresenciaEquipo {
  conteo: Record<EstadoPresencia, number>;
  tecnicos: UsuarioPresencia[];
}

/** Label of any state; unknown values are shown as they come */
export function etiquetaPresencia(estado: string): string {
  return ETIQUETAS_PRESENCIA[estado as EstadoPresencia] ?? estado;
}

/**
 * Soporte home (Django `inicio`): my presence state, the team's presence and
 * the team announcement. The backend decides who may change what: any user
 * changes their own state while on shift; only Jefe or dashboard users publish.
 */
@Injectable({ providedIn: 'root' })
export class InicioSoporteService {
  private readonly api = inject(ApiRaizService);

  miEstado(): Promise<UsuarioPresencia> {
    return this.api.get<UsuarioPresencia>('/usuarios/me');
  }

  /** Only `disponible` / `ocupado`; the backend answers 403 when off shift */
  cambiarEstado(estado: 'disponible' | 'ocupado'): Promise<void> {
    return this.api.patch<void>('/usuarios/estado', { estado_actual: estado });
  }

  /**
   * Active Técnicos and Jefes (the backend default), grouped like Django.
   * The Wilmercito assistant account is hidden: Wilmercito does not exist in Angular.
   */
  async equipo(): Promise<PresenciaEquipo> {
    const usuarios = await this.api.get<UsuarioPresencia[]>('/usuarios');
    return agruparPresencia(usuarios.filter((u) => !/wilmercito/i.test(u.display_name)));
  }

  anuncio(): Promise<AnuncioEquipo> {
    return this.api.get<AnuncioEquipo>('/announcements');
  }

  /** Replaces the current announcement; an empty message deletes it */
  publicarAnuncio(mensaje: string): Promise<AnuncioEquipo> {
    return this.api.post<AnuncioEquipo>('/announcements', { message: mensaje });
  }
}

/** Django `_presencia`: count known states and sort by state priority, then name */
export function agruparPresencia(usuarios: UsuarioPresencia[]): PresenciaEquipo {
  const conteo = { disponible: 0, ocupado: 0, extraturno: 0, ausente: 0 } as Record<EstadoPresencia, number>;
  for (const u of usuarios) {
    if (u.estado_actual in conteo) conteo[u.estado_actual as EstadoPresencia] += 1;
  }
  const prioridad = (estado: string): number => {
    const i = ORDEN_PRESENCIA.indexOf(estado as EstadoPresencia);
    return i < 0 ? 9 : i;
  };
  const tecnicos = [...usuarios].sort(
    (a, b) => prioridad(a.estado_actual) - prioridad(b.estado_actual) || a.display_name.localeCompare(b.display_name, 'es'),
  );
  return { conteo, tecnicos };
}
