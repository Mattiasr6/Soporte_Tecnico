"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDashboardStats, getUsuarios } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import type { DashboardStats } from "@/lib/api";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const COLORS = ["#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#e11d48"];

export default function PerfilPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [globalStats, setGlobalStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    const uid = Number(id);
    if (isNaN(uid)) { router.replace("/dashboard"); return; }

    Promise.all([
      getDashboardStats({ usuarioId: uid }),
      getDashboardStats(),
    ]).then(([s, g]) => {
      setStats(s);
      setGlobalStats(g);
    }).finally(() => setLoading(false));
  }, [id, user, router]);

  if (loading || !stats || !globalStats) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Cargando perfil...</span>
        </div>
      </div>
    );
  }

  const uid = Number(id);
  const tecnico = stats.porTecnico[0];
  if (!tecnico) return <p className="p-6 text-center text-slate-500">Técnico no encontrado</p>;

  const nombre = tecnico.displayName;
  const iniciales = nombre.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  const total = tecnico.total;
  const estrellas = Math.floor(total / 100);
  const promedio = Math.round(total / (stats.porMes.length || 1));

  // Especialidad: categoria con mas atenciones
  let especialidad = "General";
  let especialidadCount = 0;
  for (const c of stats.porCategoria) {
    if (c.total > especialidadCount) { especialidadCount = c.total; especialidad = c.categoria; }
  }

  // Comparativa contra el equipo
  const totalGlobal = globalStats.total || 1;
  const pctEquipo = ((total / totalGlobal) * 100).toFixed(1);
  const promedioEquipo = Math.round(totalGlobal / (globalStats.porTecnico.length || 1));
  const difPromedio = total - promedioEquipo;
  const rankingPos = globalStats.porTecnico.findIndex((t) => t.usuarioId === uid) + 1;

  // Insignias
  const badges: { label: string; desc: string; color: string }[] = [];
  if (rankingPos === 1) badges.push({ label: "🥇", desc: "Líder del equipo", color: "from-yellow-400 to-amber-600" });
  if (total >= 100) badges.push({ label: "💪", desc: "100+ atenciones", color: "from-amber-500 to-orange-600" });
  if (especialidadCount > 0) badges.push({ label: "🎯", desc: `Especialista en ${especialidad}`, color: "from-sky-500 to-blue-600" });
  if (stats.porMes.length >= 5) badges.push({ label: "📅", desc: "Constante todos los meses", color: "from-emerald-500 to-teal-600" });
  if (promedio >= 30) badges.push({ label: "⚡", desc: "Alto rendimiento", color: "from-violet-500 to-purple-600" });

  const maxCat = Math.max(...stats.porCategoria.map((c) => c.total), 1);
  const maxMes = Math.max(...stats.porMes.map((m) => m.total), 1);

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-3 py-6 lg:px-6">
      {/* Header con avatar */}
      <div className="flex flex-col items-center gap-4 rounded-2xl border border-slate-700/50 bg-gradient-to-br from-slate-800 to-slate-900 p-6 shadow-xl sm:flex-row sm:gap-6">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 text-3xl font-bold text-slate-950 shadow-lg shadow-amber-500/20">
          {iniciales}
        </div>
        <div className="flex-1 text-center sm:text-left">
          <div className="flex flex-col items-center gap-2 sm:flex-row sm:gap-3">
            <h1 className="text-2xl font-bold text-slate-100">{nombre}</h1>
            {estrellas > 0 && (
              <span className="flex gap-0.5">
                {Array.from({ length: estrellas }).map((_, s) => (
                  <svg key={s} className="h-5 w-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs uppercase tracking-wider text-slate-500">
            Técnico de Soporte · {rankingPos === 1 ? "Líder del equipo" : `#${rankingPos} en el ranking`}
          </p>
        </div>
        <button
          onClick={() => router.back()}
          className="self-start rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
        >
          ← Volver
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Atenciones" value={total} color="amber" />
        <StatCard label="Promedio x Mes" value={promedio} color="sky" />
        <StatCard label="Posición" value={`#${rankingPos}`} color="emerald" />
        <StatCard label="vs Promedio" value={difPromedio > 0 ? `+${difPromedio}` : `${difPromedio}`} color={difPromedio >= 0 ? "emerald" : "red"} />
      </div>

      {/* Porcentaje del equipo y especialidad */}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Contribución al Equipo</h3>
          <div className="flex flex-col items-center">
            <span className="text-4xl font-bold text-amber-400">{pctEquipo}%</span>
            <p className="mt-1 text-xs text-slate-500">del total del equipo ({total} de {totalGlobal})</p>
            <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-slate-700">
              <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400" style={{ width: `${pctEquipo}%` }} />
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Especialidad</h3>
          <div className="flex flex-col items-center">
            <span className="text-2xl font-bold text-sky-400">{especialidad}</span>
            <p className="mt-1 text-xs text-slate-500">{especialidadCount} atenciones en esta categoría</p>
          </div>
          <div className="mt-4 space-y-2">
            {stats.porCategoria.slice(0, 4).map((c) => (
              <div key={c.categoria} className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[stats.porCategoria.indexOf(c) % COLORS.length] }} />
                <span className="flex-1 text-slate-300 truncate">{c.categoria}</span>
                <span className="text-slate-500">{c.total}</span>
                <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-700">
                  <div className="h-full rounded-full bg-sky-500" style={{ width: `${(c.total / maxCat) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Insignias */}
      {badges.length > 0 && (
        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Logros</h3>
          <div className="flex flex-wrap gap-3">
            {badges.map((b) => (
              <div
                key={b.label}
                className={`inline-flex items-center gap-2 rounded-xl bg-gradient-to-br ${b.color} px-4 py-2.5 text-sm font-semibold text-white shadow-lg`}
              >
                <span className="text-lg">{b.label}</span>
                <span>{b.desc}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Minigrafico mensual */}
      <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Rendimiento Mensual</h3>
        <div className="flex items-end gap-2" style={{ height: "100px" }}>
          {stats.porMes.map((m) => (
            <div key={`${m.anio}-${m.mes}`} className="flex flex-1 flex-col items-center gap-1">
              <span className="text-[10px] font-medium text-slate-400">{m.total}</span>
              <div
                className="w-full rounded-t-md bg-gradient-to-t from-amber-500 to-amber-400 transition-all"
                style={{ height: `${(m.total / maxMes) * 70}px`, minHeight: m.total > 0 ? "3px" : "0px" }}
              />
              <span className="text-[9px] text-slate-500">{MONTHS[m.mes - 1]}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colors: Record<string, string> = {
    amber: "border-amber-500/30 from-amber-500/10 text-amber-400",
    sky: "border-sky-500/30 from-sky-500/10 text-sky-400",
    emerald: "border-emerald-500/30 from-emerald-500/10 text-emerald-400",
    red: "border-red-500/30 from-red-500/10 text-red-400",
  };
  return (
    <div className={`rounded-xl border bg-gradient-to-br p-4 text-center ${colors[color] ?? colors.amber}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs font-medium uppercase tracking-wider opacity-70">{label}</p>
    </div>
  );
}
