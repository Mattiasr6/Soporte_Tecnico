export interface Usuario {
  id: number;
  displayName: string;
  especialidad?: string;
  role: "Tecnico" | "Jefe" | "Auxiliar";
  estadoActual: "disponible" | "ocupado" | "ausente" | "extraturno";
  canViewDashboard: boolean;
}

export interface AtencionCreate {
  areaSolicitante: string;
  medioSolicitud: string;
  usuarioSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones?: string;
  enlaceApoyo?: string;
  colaboradorId?: number;
  fechaRegistro: string;
}

export interface AtencionRow {
  id: string;
  areaSolicitante: string;
  medioSolicitud: string;
  usuarioSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  showObservaciones: boolean;
  requiereObservaciones: boolean;
  observaciones: string;
  showEnlaceApoyo: boolean;
  enlaceApoyo: string;
  colaboradorId: number | null;
}

export interface AtencionItem {
  id: number;
  usuarioId: number;
  usuarioNombre: string;
  areaSolicitante: string;
  medioSolicitud: string;
  usuarioSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones: string | null;
  enlaceApoyo: string | null;
  colaboradorId: number | null;
  colaboradorNombre: string | null;
  fechaRegistro: string;
  fueraDeTurno: boolean;
  createdAt: string;
  grupoPadreId?: number | null;
  grupoPadreNombre?: string | null;
  grupoId?: number | null;
  grupoNombre?: string | null;
  areaId?: number | null;
  areaNombre?: string | null;
}

export interface AreaJerarquia {
  id: string;
  grupoPadre: string;
  grupo: string;
  nombre: string;
  activo: boolean;
}

export interface GrupoJerarquia {
  id: string;
  nombre: string;
  areas: AreaJerarquia[];
}

export interface PadreJerarquia {
  id: string;
  nombre: string;
  totalAreas: number;
  grupos: GrupoJerarquia[];
  areasDirectas: AreaJerarquia[];
}

export interface JerarquiaData {
  padres: PadreJerarquia[];
  areas: AreaJerarquia[];
  totalAreas: number;
}

export interface JerarquiaSelection {
  padre: PadreJerarquia | null;
  grupo: GrupoJerarquia | null;
  area: AreaJerarquia | null;
}

export interface AtencionBatchItem {
  grupoPadreId: string;
  grupoPadre: string;
  grupoId: string | null;
  grupo: string | null;
  areaId: string;
  area: string;
  medio: string;
  usuarioSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones?: string;
  enlace?: string;
  colaboradorId?: number;
  fueraDeTurno: boolean;
}
