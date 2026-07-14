import type { Usuario, AtencionCreate, AtencionItem } from "@/types";

function getApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:5000/api";
  const hostname = window.location.hostname;
  return `http://${hostname}:5000/api`;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options?.body instanceof FormData) {
  } else {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${getApiUrl()}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });

  if (res.status === 401) {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    window.location.reload();
    throw new Error("Sesión expirada");
  }

  if (!res.ok) {
    const text = await res.text();
    let msg: string;
    try {
      msg = JSON.parse(text).error || `Error ${res.status}`;
    } catch {
      msg = `Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(msg);
  }

  const text = await res.text();
  return text ? JSON.parse(text) : (undefined as T);
}

export async function getUsuarios(): Promise<Usuario[]> {
  return fetchApi("/usuarios");
}

export async function getMe(): Promise<Usuario> {
  return fetchApi("/usuarios/me");
}

export async function updateEstado(
  estadoActual: string,
  motivo?: string,
  colaboradorId?: number
): Promise<void> {
  const body: Record<string, any> = { estadoActual };
  if (motivo) body.motivo = motivo;
  if (colaboradorId) body.colaboradorId = colaboradorId;
  await fetchApi("/usuarios/estado", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function createAtenciones(
  atenciones: AtencionCreate[]
): Promise<{ registrosInsertados: number }> {
  return fetchApi("/atenciones/batch", {
    method: "POST",
    body: JSON.stringify({ atenciones }),
  });
}

export async function getAtenciones(usuarioId?: number): Promise<AtencionItem[]> {
  const query = usuarioId ? `?usuarioId=${usuarioId}` : "";
  return fetchApi(`/atenciones${query}`);
}

export async function updateAtencion(id: number, data: Record<string, any>): Promise<void> {
  await fetchApi(`/atenciones/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteAtencion(id: number): Promise<void> {
  await fetchApi(`/atenciones/${id}`, { method: "DELETE" });
}

export async function getAreas(): Promise<string[]> {
  return fetchApi("/areas");
}

export async function importCsv(file: File): Promise<{ registrosInsertados: number; errores?: string[] }> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchApi("/atenciones/import-csv", {
    method: "POST",
    body: formData,
  });
}

export interface DashboardStats {
  total: number;
  porTecnico: { usuarioId: number; displayName: string; total: number }[];
  porCategoria: { categoria: string; total: number }[];
  porMes: { anio: number; mes: number; total: number }[];
  porArea: { area: string; total: number }[];
}

export async function getDashboardStats(opts?: {
  usuarioId?: number;
  desdeMes?: number;
  desdeAnio?: number;
  hastaMes?: number;
  hastaAnio?: number;
}): Promise<DashboardStats> {
  const params = new URLSearchParams();
  if (opts?.usuarioId) params.set("usuarioId", String(opts.usuarioId));
  if (opts?.desdeMes) params.set("desdeMes", String(opts.desdeMes));
  if (opts?.desdeAnio) params.set("desdeAnio", String(opts.desdeAnio));
  if (opts?.hastaMes) params.set("hastaMes", String(opts.hastaMes));
  if (opts?.hastaAnio) params.set("hastaAnio", String(opts.hastaAnio));
  const qs = params.toString();
  return fetchApi(`/atenciones/stats${qs ? `?${qs}` : ""}`);
}

export async function sendCode(email: string): Promise<void> {
  await fetchApi("/auth/send-code", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function verifyCode(
  email: string,
  code: string
): Promise<{ token: string; user: any }> {
  return fetchApi("/auth/verify-code", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}
