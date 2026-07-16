"use client";

import { useEffect, useState } from "react";
import { Usuario } from "@/types";
import { getUsuarios } from "@/lib/api";
import { useSignalR } from "@/lib/SignalRProvider";

const estadoColor = (estado: string) => {
  switch (estado) {
    case "ocupado": return { border: "border-red-500/30", bg: "bg-gradient-to-br from-slate-800 to-slate-900", bar: "bg-red-500", ping: "bg-red-400", dot: "bg-red-500", text: "text-red-400", bgBadge: "bg-red-500/10" };
    case "disponible": return { border: "border-emerald-500/30", bg: "bg-gradient-to-br from-slate-800 to-slate-900", bar: "bg-emerald-500", ping: "bg-emerald-400", dot: "bg-emerald-500", text: "text-emerald-400", bgBadge: "bg-emerald-500/10" };
    case "extraturno": return { border: "border-amber-500/30", bg: "bg-gradient-to-br from-slate-800 to-slate-900", bar: "bg-amber-500", ping: "bg-amber-400", dot: "bg-amber-500", text: "text-amber-400", bgBadge: "bg-amber-500/10" };
    default: return { border: "border-slate-600/30", bg: "bg-gradient-to-br from-slate-800/50 to-slate-900/50", bar: "bg-slate-500", ping: "", dot: "bg-slate-500", text: "text-slate-400", bgBadge: "bg-slate-500/10" };
  }
};

const estadoLabel = (u: Usuario) => {
  if (u.estadoActual === "ocupado") return "Ocupado";
  if (u.estadoActual === "disponible") return "Disponible";
  if (u.estadoActual === "extraturno") return "Fuera de Turno";
  return "Ausente";
};

export default function DashboardCards() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const { lastStatus } = useSignalR();

  useEffect(() => {
    getUsuarios().then(setUsuarios).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Actualizar en tiempo real via SignalR
  useEffect(() => {
    if (!lastStatus) return;
    setUsuarios((prev) =>
      prev.map((u) =>
        u.id === lastStatus.usuarioId
          ? { ...u, estadoActual: lastStatus.estado as Usuario["estadoActual"] }
          : u
      )
    );
  }, [lastStatus]);

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

  const disponibles = usuarios.filter((u) => u.estadoActual === "disponible");
  const ocupados = usuarios.filter((u) => u.estadoActual === "ocupado");
  const ausentes = usuarios.filter((u) => u.estadoActual === "ausente");
  const extraturno = usuarios.filter((u) => u.estadoActual === "extraturno");

  return (
    <div className="space-y-6">
      {/* mini resumen */}
      <div className="flex gap-4 text-sm flex-wrap">
        <span className="flex items-center gap-2 text-emerald-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
          {disponibles.length} disponible{disponibles.length !== 1 ? "s" : ""}
        </span>
        <span className="flex items-center gap-2 text-red-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-400" />
          {ocupados.length} ocupado{ocupados.length !== 1 ? "s" : ""}
        </span>
        <span className="flex items-center gap-2 text-amber-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-400" />
          {extraturno.length} fuera de turno
        </span>
        <span className="flex items-center gap-2 text-slate-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-400" />
          {ausentes.length} ausente{ausentes.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* grilla de tarjetas */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {usuarios.map((u) => {
          const c = estadoColor(u.estadoActual);
          return (
            <div
              key={u.id}
              className={`group relative overflow-hidden rounded-xl border p-5 shadow-lg transition-all duration-300 hover:-translate-y-0.5 ${c.border} ${c.bg}`}
            >
              {/* barra superior decorativa */}
              <span className={`absolute left-0 right-0 top-0 h-1 ${c.bar}`} />

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-100">{u.displayName}</h3>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{u.role}</p>
                  {u.especialidad && (
                    <p className="mt-0.5 text-[11px] text-amber-400/80">{u.especialidad}</p>
                  )}
                </div>

                {/* dot pulsante */}
                <span className="relative flex h-4 w-4">
                  {u.estadoActual !== "ausente" && u.estadoActual !== "extraturno" && (
                    <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${c.ping}`} />
                  )}
                  <span className={`relative inline-flex h-4 w-4 rounded-full ${c.dot}`} />
                </span>
              </div>

              {/* etiqueta de estado */}
              <div className="mt-4 flex flex-col gap-1">
                <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${c.bgBadge} ${c.text}`}>
                  <span className={`inline-block h-1.5 w-1.5 rounded-full ${c.dot}`} />
                  {estadoLabel(u)}
                </span>
                {u.estadoActual === "extraturno" && (
                  <span className="text-[10px] text-amber-400/60">Fuera de su horario registrado</span>
                )}
                {u.estadoActual === "ocupado" && lastStatus?.usuarioId === u.id && lastStatus.motivo && (
                  <span className="text-xs text-slate-400">
                    {lastStatus.motivo === "colaborando"
                      ? `Colaborando${lastStatus.colaboradorNombre ? ` con ${lastStatus.colaboradorNombre}` : ""}`
                      : "Atendiendo un caso"}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
