import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { comprimirFoto } from './fotos';
import { EstadoCierre, Novedad, ReporteTurno, TurnoCodigo } from './modelos';

/** What the novedad form sends */
export interface NovedadNueva {
  texto: string;
  /** null: the API takes the turno of the current hour */
  turno: TurnoCodigo | null;
  ambienteId: number | null;
  foto: File | null;
}

/**
 * Lab novedades (GET/POST/DELETE /novedades, Django tab "novedades") and the
 * validation of shift closes (/reportes-turno?estado= and
 * /reportes-turno/{id}/validacion, Django tab "cierres").
 */
@Injectable({ providedIn: 'root' })
export class NovedadesService {
  private readonly api = inject(ApiService);

  /** Novedades of the last 3 days (the API applies the window), newest first */
  listar(filtros: { turno?: TurnoCodigo | null; ambienteId?: number | null } = {}): Promise<Novedad[]> {
    const params: Record<string, string | number> = {};
    if (filtros.turno) params['turno'] = filtros.turno;
    if (filtros.ambienteId) params['ambiente_id'] = filtros.ambienteId;
    return this.api.get<Novedad[]>('/novedades', params);
  }

  /** One multipart request: text, turno, lab and the reduced photo */
  async crear(n: NovedadNueva): Promise<Novedad> {
    const form = new FormData();
    form.append('texto', n.texto.trim());
    if (n.turno) form.append('turno', n.turno);
    if (n.ambienteId) form.append('ambiente_id', String(n.ambienteId));
    if (n.foto) form.append('foto', await comprimirFoto(n.foto), 'foto.jpg');
    return this.api.postForm<Novedad>('/novedades', form);
  }

  eliminar(id: number): Promise<void> {
    return this.api.delete(`/novedades/${id}`);
  }

  fotoNovedad(id: number): Promise<Blob> {
    return this.api.getBlob(`/novedades/${id}/foto`);
  }

  /** Shift closes in one estado, newest first */
  listarCierres(estado: EstadoCierre, limite = 100): Promise<ReporteTurno[]> {
    return this.api.get<ReporteTurno[]>('/reportes-turno', { estado, limite });
  }

  /** Validate or reject a pending close (Jefe/Encargado, never the author) */
  decidirCierre(id: number, estado: Exclude<EstadoCierre, 'pendiente'>): Promise<ReporteTurno> {
    return this.api.post<ReporteTurno>(`/reportes-turno/${id}/validacion`, { estado });
  }

  fotoCierre(id: number): Promise<Blob> {
    return this.api.getBlob(`/reportes-turno/${id}/foto`);
  }
}
