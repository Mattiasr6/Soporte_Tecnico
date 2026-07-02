"use client";

import { useEffect, useState, useRef } from "react";
import { useAuth } from "./AuthProvider";
import { useToast } from "./Toast";

export default function BlocNotas({ onClose }: { onClose: () => void }) {
  const { token } = useAuth();
  const { toast } = useToast();
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(true);
  const [modificado, setModificado] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!token) return;
    getApi("/usuarios/notas")
      .then((res) => res.json().then((d) => setTexto(d.contenido ?? "")))
      .catch(() => {})
      .finally(() => setCargando(false));
  }, [token]);

  function getApi(path: string, opts?: RequestInit) {
    const hostname = window.location.hostname;
    return fetch(`http://${hostname}:5000/api${path}`, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...opts?.headers,
      },
    });
  }

  function handleChange(val: string) {
    setTexto(val);
    setModificado(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      getApi("/usuarios/notas", {
        method: "PUT",
        body: JSON.stringify({ contenido: val }),
      }).catch(() => {});
      setModificado(false);
    }, 800);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-16 backdrop-blur-sm">
      <div className="mx-4 flex w-full max-w-2xl flex-col rounded-2xl border border-slate-700/50 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-700/50 px-5 py-3">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <h2 className="text-sm font-bold text-slate-100">Bloc de Notas</h2>
            {modificado && <span className="text-[10px] text-amber-400">Guardando...</span>}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500">Auto-guardado</span>
            <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white">Cerrar</button>
          </div>
        </div>
        <div className="p-4">
          {cargando ? (
            <div className="flex justify-center py-12 text-slate-500">
              <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="ml-2 text-sm">Cargando notas...</span>
            </div>
          ) : (
            <textarea
              value={texto}
              onChange={(e) => handleChange(e.target.value)}
              className="h-[50vh] w-full resize-none rounded-xl border border-slate-700 bg-slate-800/60 p-4 text-sm text-slate-200 placeholder-slate-600 transition focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
              placeholder="Escribe lo que quieras recordar..."
              style={{ fontFamily: "monospace", lineHeight: "1.6" }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
