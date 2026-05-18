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

export async function updateEstado(estadoActual: boolean): Promise<void> {
  await fetchApi("/usuarios/estado", {
    method: "PATCH",
    body: JSON.stringify({ estadoActual }),
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
