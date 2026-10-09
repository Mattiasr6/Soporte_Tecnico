import { computed, inject, Injectable, signal } from '@angular/core';
import {
  Ambiente, AmbientePc, BloqueHorario, Carrera, Docente, Feriado, Materia, SistemaAcademico, TipoReserva,
} from './modelos';
import { ApiService } from './api.service';

/** Tablas de catálogo que se guardan en memoria */
export type TablaCatalogo =
  | 'carreras' | 'docentes' | 'materias' | 'ambientes' | 'ambiente_pcs' | 'sistemas_academicos'
  | 'bloques_horario' | 'tipos_reserva' | 'feriados';

/**
 * Catálogos en memoria (carreras, docentes, ambientes, periodos…).
 * Se cargan una vez y se refrescan cuando se editan.
 */
@Injectable({ providedIn: 'root' })
export class CatalogosService {
  private readonly api = inject(ApiService);

  readonly carreras = signal<Carrera[]>([]);
  readonly docentes = signal<Docente[]>([]);
  readonly materias = signal<Materia[]>([]);
  readonly ambientes = signal<Ambiente[]>([]);
  readonly pcs = signal<AmbientePc[]>([]);
  readonly sistemas = signal<SistemaAcademico[]>([]);
  readonly bloques = signal<BloqueHorario[]>([]);
  readonly tiposReserva = signal<TipoReserva[]>([]);
  readonly feriados = signal<Feriado[]>([]);
  readonly cargado = signal(false);

  /** Mapas por id para búsquedas rápidas en las vistas */
  readonly mapaAmbientes = computed(() => new Map(this.ambientes().map((a) => [a.id, a])));
  /** PCs agrupadas por laboratorio (ambiente_id -> lista ordenada) */
  readonly pcsPorAmbiente = computed(() => {
    const mapa = new Map<number, AmbientePc[]>();
    for (const pc of this.pcs()) mapa.set(pc.ambiente_id, [...(mapa.get(pc.ambiente_id) ?? []), pc]);
    return mapa;
  });
  readonly mapaDocentes = computed(() => new Map(this.docentes().map((d) => [d.id, d])));
  readonly mapaCarreras = computed(() => new Map(this.carreras().map((c) => [c.id, c])));
  readonly mapaMaterias = computed(() => new Map(this.materias().map((m) => [m.id, m])));
  readonly mapaSistemas = computed(() => new Map(this.sistemas().map((s) => [s.id, s])));
  readonly conjuntoFeriados = computed(() => new Set(this.feriados().map((f) => f.fecha)));

  /** Ambientes utilizables (no dados de baja) */
  readonly ambientesActivos = computed(() => this.ambientes().filter((a) => a.estado !== 'baja'));
  /** Solo laboratorios no dados de baja */
  readonly laboratorios = computed(() => this.ambientesActivos().filter((a) => a.tipo === 'laboratorio'));
  /** Docentes activos ordenados por apellido */
  readonly docentesActivos = computed(() => this.docentes().filter((d) => d.activo));

  private carga: Promise<void> | null = null;

  /** Carga todos los catálogos (solo la primera vez) */
  cargarTodo(): Promise<void> {
    if (!this.carga) {
      this.carga = Promise.all([
        this.recargar('carreras'), this.recargar('docentes'), this.recargar('materias'),
        this.recargar('ambientes'), this.recargar('ambiente_pcs'), this.recargar('sistemas_academicos'),
        this.recargar('bloques_horario'), this.recargar('tipos_reserva'), this.recargar('feriados'),
      ]).then(() => this.cargado.set(true))
        .catch((e) => { this.carga = null; throw e; });
    }
    return this.carga;
  }

  /** Re-reads a catalog from the API (same ordering and embeds as the old PostgREST query) */
  async recargar(tabla: TablaCatalogo): Promise<void> {
    switch (tabla) {
      case 'carreras':
        this.carreras.set(await this.api.get<Carrera[]>('/carreras'));
        break;
      case 'docentes':
        this.docentes.set(await this.api.get<Docente[]>('/docentes'));
        break;
      case 'materias':
        this.materias.set(await this.api.get<Materia[]>('/materias'));
        break;
      case 'ambientes':
        // El sistema maneja solo laboratorios (las aulas se registran como texto al reubicar)
        this.ambientes.set(await this.api.get<Ambiente[]>('/ambientes', { tipo: 'laboratorio' }));
        break;
      case 'ambiente_pcs':
        this.pcs.set(await this.api.get<AmbientePc[]>('/ambiente-pcs'));
        break;
      case 'sistemas_academicos':
        this.sistemas.set(await this.api.get<SistemaAcademico[]>('/sistemas-academicos'));
        break;
      case 'bloques_horario':
        this.bloques.set(await this.api.get<BloqueHorario[]>('/bloques-horario'));
        break;
      case 'tipos_reserva':
        this.tiposReserva.set(await this.api.get<TipoReserva[]>('/tipos-reserva'));
        break;
      case 'feriados':
        this.feriados.set(await this.api.get<Feriado[]>('/feriados'));
        break;
    }
  }

  /**
   * Inserta o actualiza una fila de un catálogo y refresca la lista.
   * Key 'id': no id -> POST (create), id -> PATCH (update).
   * Other key (feriados by fecha): PUT (create or replace, like the old upsert).
   * @returns la fila guardada
   */
  async guardar<T extends object>(tabla: TablaCatalogo, fila: T, clave = 'id'): Promise<T> {
    const path = editablePath(tabla);
    const body = { ...fila } as Record<string, unknown>;
    const key = body[clave];
    delete body[clave];
    let saved: T;
    if (clave !== 'id') {
      saved = await this.api.put<T>(`${path}/${encodeURIComponent(String(key))}`, body);
    } else if (key !== undefined && key !== null) {
      saved = await this.api.patch<T>(`${path}/${key}`, body);
    } else {
      saved = await this.api.post<T>(path, body);
    }
    await this.recargar(tabla);
    return saved;
  }

  /** Elimina una fila de un catálogo y refresca la lista */
  async eliminar(tabla: TablaCatalogo, valor: unknown, _clave = 'id'): Promise<void> {
    await this.api.delete(`${editablePath(tabla)}/${encodeURIComponent(String(valor))}`);
    await this.recargar(tabla);
  }

  /** Replaces a docente's carreras and materias (one transaction) and refreshes the list */
  async guardarRelacionesDocente(docenteId: number, carreras: number[], materias: number[]): Promise<void> {
    await this.api.put(`/docentes/${docenteId}/relaciones`, { carreras, materias });
    await this.recargar('docentes');
  }

  /** Nombre "Apellidos Nombres" de un docente */
  nombreDocente(id: number | null | undefined): string {
    if (!id) return '';
    const docente = this.mapaDocentes().get(id);
    return docente ? `${docente.apellidos} ${docente.nombres}` : `Docente #${id}`;
  }

  /** Código del ambiente (LAB-01…) */
  codigoAmbiente(id: number | null | undefined): string {
    if (!id) return '—';
    return this.mapaAmbientes().get(id)?.codigo ?? `#${id}`;
  }
}

/** Catalogs the app edits, and their API path */
const EDITABLE_PATHS: Partial<Record<TablaCatalogo, string>> = {
  carreras: '/carreras',
  docentes: '/docentes',
  materias: '/materias',
  ambientes: '/ambientes',
  ambiente_pcs: '/ambiente-pcs',
  feriados: '/feriados',
};

function editablePath(tabla: TablaCatalogo): string {
  const path = EDITABLE_PATHS[tabla];
  if (!path) throw new Error(`El catálogo ${tabla} no se edita desde la aplicación.`);
  return path;
}
