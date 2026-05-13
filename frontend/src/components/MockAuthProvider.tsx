"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface MockUser {
  id: number;
  displayName: string;
  role: string;
  email: string;
  microsoftId: string;
}

interface MockAuthContextValue {
  user: MockUser | null;
  login: (userId: number) => void;
  logout: () => void;
}

const MOCK_USERS: MockUser[] = [
  {
    id: 1,
    displayName: "Carlos Méndez",
    role: "Jefe",
    email: "carlos@empresa.com",
    microsoftId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  },
  {
    id: 2,
    displayName: "Ana López",
    role: "Tecnico",
    email: "ana@empresa.com",
    microsoftId: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  },
  {
    id: 3,
    displayName: "Pedro Ramírez",
    role: "Tecnico",
    email: "pedro@empresa.com",
    microsoftId: "c3d4e5f6-a7b8-9012-cdef-123456789012",
  },
];

const MockAuthContext = createContext<MockAuthContextValue>(null!);

export const useMockAuth = () => useContext(MockAuthContext);

export default function MockAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MockUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = localStorage.getItem("mockUser");
    if (raw) {
      try {
        setUser(JSON.parse(raw));
      } catch {}
    }
    setLoading(false);
  }, []);

  const login = (userId: number) => {
    const found = MOCK_USERS.find((u) => u.id === userId);
    if (found) {
      localStorage.setItem("mockUser", JSON.stringify(found));
      setUser(found);
    }
  };

  const logout = () => {
    localStorage.removeItem("mockUser");
    setUser(null);
  };

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
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 shadow-lg shadow-amber-500/25">
            <svg className="h-8 w-8 text-slate-950" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7m-7.39-7.39l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-100">Soporte Técnico</h1>
          <p className="mt-1 text-sm text-slate-500">
            Selecciona un usuario para iniciar sesión
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-4">
          <button
            onClick={() => login(1)}
            className="group w-52 rounded-xl border border-slate-700 bg-slate-800/60 p-5 text-left shadow-lg backdrop-blur-sm transition hover:border-amber-500/50 hover:bg-slate-800"
          >
            <p className="text-base font-semibold text-slate-100 group-hover:text-amber-400">
              Carlos Méndez
            </p>
            <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-slate-500">
              Jefe
            </p>
          </button>
          <button
            onClick={() => login(2)}
            className="group w-52 rounded-xl border border-slate-700 bg-slate-800/60 p-5 text-left shadow-lg backdrop-blur-sm transition hover:border-emerald-500/50 hover:bg-slate-800"
          >
            <p className="text-base font-semibold text-slate-100 group-hover:text-emerald-400">
              Ana López
            </p>
            <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-slate-500">
              Técnico
            </p>
          </button>
          <button
            onClick={() => login(3)}
            className="group w-52 rounded-xl border border-slate-700 bg-slate-800/60 p-5 text-left shadow-lg backdrop-blur-sm transition hover:border-purple-500/50 hover:bg-slate-800"
          >
            <p className="text-base font-semibold text-slate-100 group-hover:text-purple-400">
              Pedro Ramírez
            </p>
            <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-slate-500">
              Técnico
            </p>
          </button>
        </div>
      </div>
    );
  }

  return (
    <MockAuthContext.Provider value={{ user, login, logout }}>
      {children}
    </MockAuthContext.Provider>
  );
}
