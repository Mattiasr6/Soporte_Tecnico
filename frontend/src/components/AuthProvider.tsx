"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { sendCode, verifyCode } from "@/lib/api";

interface User {
  id: number;
  displayName: string;
  role: string;
  email: string;
  estadoActual: boolean;
  canViewDashboard: boolean;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loginStep1: (email: string) => Promise<void>;
  loginStep2: (code: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  error: string | null;
  step: "email" | "code";
  email: string;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthContextValue>(null!);

export const useAuth = () => useContext(AuthContext);

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [rememberMe, setRememberMe] = useState(true);

  const storage = useCallback(() => rememberMe ? localStorage : sessionStorage, [rememberMe]);

  useEffect(() => {
    const s = window.localStorage;
    const storedToken = s.getItem("auth_token") || window.sessionStorage.getItem("auth_token");
    const storedUser = s.getItem("auth_user") || window.sessionStorage.getItem("auth_user");
    const storedRemember = s.getItem("auth_remember");
    if (storedRemember !== null) setRememberMe(storedRemember === "true");
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

  const loginStep1 = useCallback(async (emailInput: string) => {
    setError(null);
    const normalized = emailInput.trim().toLowerCase();

    if (!normalized) {
      setError("Ingresa tu correo institucional");
      return;
    }

    try {
      await sendCode(normalized);
      setEmail(normalized);
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar el codigo");
    }
  }, []);

  const loginStep2 = useCallback(async (code: string) => {
    setError(null);

    if (!code || code.length !== 6) {
      setError("Ingresa el codigo de 6 digitos");
      return;
    }

    try {
      const data = await verifyCode(email, code);
      const s = rememberMe ? localStorage : sessionStorage;
      s.setItem("auth_token", data.token);
      s.setItem("auth_user", JSON.stringify(data.user));
      localStorage.setItem("auth_remember", String(rememberMe));
      setToken(data.token);
      setUser(data.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Codigo invalido");
    }
  }, [email, rememberMe]);

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    localStorage.removeItem("auth_remember");
    sessionStorage.removeItem("auth_token");
    sessionStorage.removeItem("auth_user");
    setToken(null);
    setUser(null);
    setStep("email");
    setEmail("");
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
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 shadow-lg shadow-amber-500/25">
            <svg className="h-8 w-8 text-slate-950" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7m-7.39-7.39l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-100">Soporte Técnico</h1>
          <p className="mt-1 text-sm text-slate-500">
            Inicia sesión para continuar
          </p>
        </div>

        {step === "email" ? (
          <EmailForm onSubmit={loginStep1} error={error} rememberMe={rememberMe} onRememberChange={setRememberMe} />
        ) : (
          <CodeForm email={email} onSubmit={loginStep2} onBack={() => { setStep("email"); setError(null); }} error={error} />
        )}
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, loginStep1, loginStep2, logout, loading, error, step, email, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

function EmailForm({ onSubmit, error, rememberMe, onRememberChange }: { onSubmit: (email: string) => Promise<void>; error: string | null; rememberMe: boolean; onRememberChange: (v: boolean) => void; }) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setLocalError(null);
    try {
      await onSubmit(email);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
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
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="tu@UPDS.edu.bo"
          required
          className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 backdrop-blur-sm transition focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
        />
      </div>

      <label className="mb-4 flex cursor-pointer items-center gap-2 text-xs text-slate-400">
        <input
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => onRememberChange(e.target.checked)}
          className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-amber-500 focus:ring-amber-500/50"
        />
        Recordar sesión
      </label>

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 px-4 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-amber-500/25 transition hover:from-amber-400 hover:to-amber-500 disabled:opacity-50"
      >
        {submitting ? "Enviando..." : "Enviar código"}
      </button>
    </form>
  );
}

function CodeForm({ email, onSubmit, onBack, error }: { email: string; onSubmit: (code: string) => Promise<void>; onBack: () => void; error: string | null }) {
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setLocalError(null);
    try {
      await onSubmit(code);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm">
      <p className="mb-4 text-center text-sm text-slate-400">
        Código enviado a <span className="font-medium text-slate-300">{email}</span>
      </p>

      {displayError && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
          {displayError}
        </div>
      )}

      <div className="mb-4">
        <label htmlFor="code" className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">
          Código de verificación
        </label>
        <input
          id="code"
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          placeholder="123456"
          required
          autoFocus
          className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3 text-center text-2xl tracking-[0.5em] text-slate-100 placeholder-slate-600 backdrop-blur-sm transition focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
        />
      </div>

      <button
        type="submit"
        disabled={submitting || code.length !== 6}
        className="w-full rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 px-4 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-amber-500/25 transition hover:from-amber-400 hover:to-amber-500 disabled:opacity-50"
      >
        {submitting ? "Verificando..." : "Verificar código"}
      </button>

      <button
        type="button"
        onClick={onBack}
        className="mt-3 w-full text-center text-sm text-slate-500 transition hover:text-slate-300"
      >
        ← Usar otro correo
      </button>
    </form>
  );
}
