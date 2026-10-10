import { inject, Injectable } from '@angular/core';
import { ApiRaizService } from './api.service';

/** Max length the backend accepts (`SugerenciaIn.texto`, max_length=1000) */
export const MAXIMO_SUGERENCIA = 1000;

/** One suggestion as GET/POST /api/sugerencias returns it (`SugerenciaOut`) */
export interface Sugerencia {
  id: number;
  usuario_id: number;
  autor: string;
  texto: string;
  /** pendiente | revisada | descartada */
  estado: string;
  /** ISO date-time */
  fecha: string;
}

/**
 * Suggestion box (Django `sugerencias`): every logged-in user reads all
 * suggestions and sends new ones. Changing the state (PATCH, Jefe only) has
 * no screen in Django, so it is not exposed here either.
 */
@Injectable({ providedIn: 'root' })
export class SugerenciasService {
  private readonly api = inject(ApiRaizService);

  listar(): Promise<Sugerencia[]> {
    return this.api.get<Sugerencia[]>('/sugerencias');
  }

  enviar(texto: string): Promise<Sugerencia> {
    return this.api.post<Sugerencia>('/sugerencias', { texto });
  }
}
