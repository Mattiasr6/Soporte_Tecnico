"use client";

import { useEffect, useState } from "react";
import { getMe } from "@/lib/api";
import type { Usuario } from "@/types";

export default function Home() {
  const [user, setUser] = useState<Usuario | null>(null);
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {});
  }, []);

  const logout = () => {
    localStorage.removeItem("mockUser");
    window.location.reload();
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      {/* logo / título */}
      <div className="mb-6 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 shadow-lg shadow-amber-500/25">
          <svg className="h-8 w-8 text-slate-950" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7m-7.39-7.39l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-slate-100">Soporte Técnico</h1>
        <p className="mt-1 text-sm text-slate-500">
          Sistema de registro de atenciones
        </p>
      </div>

      {/* bienvenida */}
      {user && (
        <div className="mb-8 rounded-xl border border-slate-800 bg-slate-900/60 px-6 py-4 text-center shadow-lg backdrop-blur-sm">
          <p className="text-lg text-slate-200">
            Bienvenido, <span className="font-semibold text-slate-100">{user.displayName}</span>
          </p>
          <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-slate-500">
            {user.role}
          </p>
        </div>
      )}

      {/* navegación */}
      <div className="flex flex-wrap gap-4">
        <a
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-6 py-3 text-sm font-medium text-slate-200 shadow-lg backdrop-blur-sm transition hover:border-emerald-500/50 hover:bg-slate-800 hover:text-emerald-400"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
          </svg>
          Dashboard
        </a>
        <a
          href="/soporte"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-6 py-3 text-sm font-medium text-slate-200 shadow-lg backdrop-blur-sm transition hover:border-amber-500/50 hover:bg-slate-800 hover:text-amber-400"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7m-7.39-7.39l2.15-2.15a2.5 2.5 0 013.53 0l.7.7a2.5 2.5 0 010 3.53l-3.51 3.51a2.5 2.5 0 01-3.53 0l-.7-.7" />
          </svg>
          Soporte
        </a>
      </div>

      {/* logout */}
      {isMock && (
        <button
          onClick={logout}
          className="mt-12 text-sm text-slate-600 transition hover:text-slate-400"
        >
          Volver al inicio de sesión
        </button>
      )}
    </main>
  );
}
