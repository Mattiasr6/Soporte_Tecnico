"use client";

import { useEffect, useState } from "react";
import { Usuario } from "@/types";
import { getUsuarios } from "@/lib/api";

export default function DashboardCards() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await getUsuarios();
        setUsuarios(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-slate-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Cargando técnicos...</span>
        </div>
      </div>
    );
  }

  const disponibles = usuarios.filter((u) => !u.estadoActual);
  const ocupados = usuarios.filter((u) => u.estadoActual);

  return (
    <div className="space-y-6">
      {/* mini resumen */}
      <div className="flex gap-4 text-sm">
        <span className="flex items-center gap-2 text-emerald-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
          {disponibles.length} disponible{disponibles.length !== 1 ? "s" : ""}
        </span>
        <span className="flex items-center gap-2 text-red-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-400" />
          {ocupados.length} ocupado{ocupados.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* grilla de tarjetas */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {usuarios.map((u) => (
          <div
            key={u.id}
            className={`group relative overflow-hidden rounded-xl border p-5 shadow-lg transition-all duration-300 hover:-translate-y-0.5 ${
              u.estadoActual
                ? "border-red-500/30 bg-gradient-to-br from-slate-800 to-slate-900"
                : "border-emerald-500/30 bg-gradient-to-br from-slate-800 to-slate-900"
            }`}
          >
            {/* barra superior decorativa */}
            <span
              className={`absolute left-0 right-0 top-0 h-1 ${
                u.estadoActual ? "bg-red-500" : "bg-emerald-500"
              }`}
            />

            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-100">
                  {u.displayName}
                </h3>
                <p className="mt-0.5 text-xs font-medium uppercase tracking-wider text-slate-500">
                  {u.role}
                </p>
              </div>

              {/* dot pulsante */}
              <span className="relative flex h-4 w-4">
                <span
                  className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                    u.estadoActual ? "bg-red-400" : "bg-emerald-400"
                  }`}
                />
                <span
                  className={`relative inline-flex h-4 w-4 rounded-full ${
                    u.estadoActual ? "bg-red-500" : "bg-emerald-500"
                  }`}
                />
              </span>
            </div>

            {/* etiqueta de estado */}
            <div className="mt-4 flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  u.estadoActual
                    ? "bg-red-500/10 text-red-400"
                    : "bg-emerald-500/10 text-emerald-400"
                }`}
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    u.estadoActual ? "bg-red-400" : "bg-emerald-400"
                  }`}
                />
                {u.estadoActual ? "Ocupado" : "Disponible"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
