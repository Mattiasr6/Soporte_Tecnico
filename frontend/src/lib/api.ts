import {
  PublicClientApplication,
  AccountInfo,
} from "@azure/msal-browser";
import { loginRequest, apiConfig } from "./authConfig";
import type { Usuario, AtencionCreate } from "@/types";

let msalInstance: PublicClientApplication | null = null;

export function setMsalInstance(instance: PublicClientApplication) {
  msalInstance = instance;
}

const isMock = () =>
  typeof window !== "undefined" &&
  process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";

function getMockUserId(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("mockUser");
    return raw ? JSON.parse(raw).id : null;
  } catch {
    return null;
  }
}

function getAccount(): AccountInfo {
  if (!msalInstance) throw new Error("MSAL no inicializado");
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) throw new Error("No hay sesión activa");
  return accounts[0];
}

async function getToken(): Promise<string> {
  const account = getAccount();
  const response = await msalInstance!.acquireTokenSilent({
    ...loginRequest,
    account,
  });
  return response.accessToken;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (isMock()) {
    const userId = getMockUserId();
    if (userId) {
      headers["X-Mock-User-Id"] = String(userId);
    }
  } else {
    const token = await getToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${apiConfig.baseUrl}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });
  if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`);
  const text = await res.text();
  return text ? JSON.parse(text) : undefined;
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
