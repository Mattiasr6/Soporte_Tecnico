import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { EstadoSoftwarePc, PlantillaAtencion, PlantillaNueva, Software, SoftwareNuevo, SoftwarePc } from './modelos';

/**
 * Software inventory and attention templates (G7, Django `auxiliares/software/`):
 * catalogue, the software list of each lab, the state of each software on a PC
 * and the templates that prefill a lab attention.
 */
@Injectable({ providedIn: 'root' })
export class SoftwareService {
  private readonly api = inject(ApiService);

  listar(): Promise<Software[]> {
    return this.api.get<Software[]>('/software');
  }

  crear(s: SoftwareNuevo): Promise<Software> {
    return this.api.post<Software>('/software', s);
  }

  editar(id: number, s: SoftwareNuevo): Promise<Software> {
    return this.api.put<Software>(`/software/${id}`, s);
  }

  eliminar(id: number): Promise<void> {
    return this.api.delete(`/software/${id}`);
  }

  /** Software installed in a lab */
  deLaboratorio(ambienteId: number): Promise<Software[]> {
    return this.api.get<Software[]>(`/ambientes/${ambienteId}/software`);
  }

  /** Replaces the whole software list of a lab */
  definirDeLaboratorio(ambienteId: number, softwareIds: number[]): Promise<{ software_ids: number[] }> {
    return this.api.put(`/ambientes/${ambienteId}/software`, { software_ids: softwareIds });
  }

  /** Software of the PC's lab with its state on the PC */
  dePc(pcId: number): Promise<SoftwarePc[]> {
    return this.api.get<SoftwarePc[]>(`/ambiente-pcs/${pcId}/software`);
  }

  /** Sets the state; a real change also records a "programas" attention */
  marcarEnPc(pcId: number, softwareId: number, estado: EstadoSoftwarePc): Promise<{ atencion_id: number | null }> {
    return this.api.put(`/ambiente-pcs/${pcId}/software/${softwareId}`, { estado });
  }

  plantillas(soloActivas = false): Promise<PlantillaAtencion[]> {
    return this.api.get<PlantillaAtencion[]>('/plantillas-atencion', soloActivas ? { activas: true } : undefined);
  }

  crearPlantilla(p: PlantillaNueva): Promise<PlantillaAtencion> {
    return this.api.post<PlantillaAtencion>('/plantillas-atencion', p);
  }

  editarPlantilla(id: number, p: PlantillaNueva): Promise<PlantillaAtencion> {
    return this.api.put<PlantillaAtencion>(`/plantillas-atencion/${id}`, p);
  }

  eliminarPlantilla(id: number): Promise<void> {
    return this.api.delete(`/plantillas-atencion/${id}`);
  }
}
