export interface Usuario {
  id: number;
  displayName: string;
  role: "Tecnico" | "Jefe";
  estadoActual: boolean;
}

export interface AtencionCreate {
  areaSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  observaciones?: string;
  fechaRegistro: string;
}

export interface AtencionRow {
  id: string;
  areaSolicitante: string;
  categoria: string;
  descripcion: string;
  solucion: string;
  showObservaciones: boolean;
  requiereObservaciones: boolean;
  observaciones: string;
}
