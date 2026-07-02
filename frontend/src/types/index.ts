export interface Usuario {
  id: number;
  displayName: string;
  role: "Tecnico" | "Jefe";
  estadoActual: boolean;
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
  fechaRegistro: string;
  createdAt: string;
}
