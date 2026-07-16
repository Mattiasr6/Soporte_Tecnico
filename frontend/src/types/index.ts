export interface Usuario {
  id: number;
  displayName: string;
  especialidad?: string;
  role: "Tecnico" | "Jefe";
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
}
