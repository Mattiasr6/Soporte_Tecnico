"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

interface User {
  id: number;
  displayName: string;
  role: string;
  email: string;
  estadoActual: string;
  canViewDashboard: boolean;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  error: string | null;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthContextValue>(null!);
export const useAuth = () => useContext(AuthContext);

function getApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:5000/api";
  return `http://${window.location.hostname}:5000/api`;
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const storage = useCallback(() => localStorage, []);

  useEffect(() => {
    const s = window.localStorage;
    const storedToken = s.getItem("auth_token") || window.sessionStorage.getItem("auth_token");
    const storedUser = s.getItem("auth_user") || window.sessionStorage.getItem("auth_user");
    const storedRemember = s.getItem("auth_remember");
    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      } catch {
        s.removeItem("auth_token");
        s.removeItem("auth_user");
        window.sessionStorage.removeItem("auth_token");
        window.sessionStorage.removeItem("auth_user");
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    const normalized = email.trim().toLowerCase();
    if (!normalized || !password) {
      setError("Ingresa correo y contraseña");
      return;
    }
    try {
      const res = await fetch(`${getApiUrl()}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalized, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Error al iniciar sesión");
        return;
      }
      const s = localStorage;
      s.setItem("auth_token", data.token);
      s.setItem("auth_user", JSON.stringify(data.user));
      localStorage.setItem("auth_remember", "true");
      setToken(data.token);
      setUser(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexión");
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    localStorage.removeItem("auth_remember");
    sessionStorage.removeItem("auth_token");
    sessionStorage.removeItem("auth_user");
    setToken(null);
    setUser(null);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex items-center gap-3 text-slate-500">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Cargando...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginForm onLogin={login} error={error} />;
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, error, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

function LoginForm({ onLogin, error }: { onLogin: (email: string, pass: string) => Promise<void>; error: string | null }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setLocalError(null);
    try {
      await onLogin(email, password);
    } catch {
      setLocalError("Error al iniciar sesión");
    } finally {
      setSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 shadow-lg shadow-amber-500/25">
          <svg className="h-8 w-8 text-slate-950" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7m-7.39-7.39l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-slate-100">Soporte Técnico</h1>
        <p className="mt-1 text-sm text-slate-500">Inicia sesión con tu correo institucional</p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-sm">
        {displayError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
            {displayError}
          </div>
        )}

        <div className="mb-4">
          <label htmlFor="email" className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">
            Correo institucional
          </label>
          <input
            id="email" type="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ejemplo@upds.edu.bo" required autoFocus
            className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 backdrop-blur-sm transition focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="password" className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">
            Contraseña
          </label>
          <input
            id="password" type="password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Ingresa tu contraseña" required
            className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 backdrop-blur-sm transition focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
          />
        </div>

        <button type="submit" disabled={submitting}
          className="w-full rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 px-4 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-amber-500/25 transition hover:from-amber-400 hover:to-amber-500 disabled:opacity-50">
          {submitting ? "Ingresando..." : "Ingresar"}
        </button>
      </form>
    </div>
  );
}
