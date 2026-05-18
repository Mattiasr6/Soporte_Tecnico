"use client";

import { useEffect, useState } from "react";
import { getAtenciones, getUsuarios } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import type { AtencionItem, Usuario } from "@/types";

export default function HistorialModal({ onClose }: { onClose: () => void }) {
  const { user } = useAuth();
  const [atenciones, setAtenciones] = useState<AtencionItem[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [filtroUsuario, setFiltroUsuario] = useState<number | "">("");
  const [loading, setLoading] = useState(true);

  const isJefe = user?.role === "Jefe";

  useEffect(() => {
    if (isJefe) {
      getUsuarios().then(setUsuarios).catch(() => {});
    }
  }, [isJefe]);

  useEffect(() => {
    setLoading(true);
    getAtenciones(filtroUsuario || undefined)
      .then(setAtenciones)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filtroUsuario]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-10 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-5xl rounded-2xl border border-slate-700/50 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-700/50 px-6 py-4">
          <h2 className="text-lg font-bold text-slate-100">Historial de Atenciones</h2>
          <div className="flex items-center gap-3">
            {isJefe && (
              <select
                value={filtroUsuario}
                onChange={(e) => setFiltroUsuario(e.target.value ? Number(e.target.value) : "")}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
              >
                <option value="">Todos los técnicos</option>
                {usuarios.map((u) => (
                  <option key={u.id} value={u.id}>{u.displayName}</option>
                ))}
              </select>
            )}
            <button
              onClick={onClose}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white"
            >
              Cerrar
            </button>
          </div>
        </div>

        <div className="max-h-[70vh] overflow-auto p-6">
          {loading ? (
            <div className="flex justify-center py-12 text-slate-500">
              <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="ml-2 text-sm">Cargando...</span>
            </div>
          ) : atenciones.length === 0 ? (
            <p className="py-12 text-center text-sm text-slate-500">No hay atenciones registradas.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400">
                    <th className="whitespace-nowrap p-2 text-left font-semibold">Fecha</th>
                    {isJefe && <th className="whitespace-nowrap p-2 text-left font-semibold">Técnico</th>}
                    <th className="whitespace-nowrap p-2 text-left font-semibold">Área</th>
                    <th className="whitespace-nowrap p-2 text-left font-semibold">Medio</th>
                    <th className="whitespace-nowrap p-2 text-left font-semibold">Usuario</th>
                    <th className="whitespace-nowrap p-2 text-left font-semibold">Categoría</th>
                    <th className="p-2 text-left font-semibold">Descripción</th>
                    <th className="p-2 text-left font-semibold">Solución</th>
                  </tr>
                </thead>
                <tbody>
                  {atenciones.map((a) => (
                    <tr key={a.id} className="border-b border-slate-800 text-slate-300 transition-colors hover:bg-slate-800/40">
                      <td className="whitespace-nowrap p-2 text-xs">{a.fechaRegistro}</td>
                      {isJefe && <td className="whitespace-nowrap p-2 text-xs text-slate-400">{a.usuarioNombre}</td>}
                      <td className="whitespace-nowrap p-2 text-xs">{a.areaSolicitante}</td>
                      <td className="whitespace-nowrap p-2 text-xs">{a.medioSolicitud}</td>
                      <td className="whitespace-nowrap p-2 text-xs">{a.usuarioSolicitante}</td>
                      <td className="whitespace-nowrap p-2 text-xs">{a.categoria}</td>
                      <td className="max-w-[200px] truncate p-2 text-xs">{a.descripcion}</td>
                      <td className="max-w-[200px] truncate p-2 text-xs">{a.solucion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="border-t border-slate-700/50 px-6 py-3 text-right text-xs text-slate-500">
          {atenciones.length} registro{atenciones.length !== 1 ? "s" : ""}
        </div>
      </div>
    </div>
  );
}
