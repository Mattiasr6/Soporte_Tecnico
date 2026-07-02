"use client";

import { useEffect, useState, useRef } from "react";
import { getDashboardStats, getUsuarios, type DashboardStats } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function ReportePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const printRef = useRef<HTMLDivElement>(null);

  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) router.replace("/soporte");
  }, [user, canAccess, router]);

  useEffect(() => {
    if (!canAccess) return;
    setLoading(true);
    getDashboardStats({ desdeMes: 1, desdeAnio: 2026, hastaMes: 6, hastaAnio: 2026 })
      .then(setStats)
      .finally(() => setLoading(false));
  }, [canAccess]);

  if (!user || !canAccess) return null;
  if (loading || !stats) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Generando reporte...</span>
        </div>
      </div>
    );
  }

  const maxBar = Math.max(...stats.porTecnico.map((t) => t.total), 1);
  const maxCat = Math.max(...stats.porCategoria.map((c) => c.total), 1);
  const totalAtenciones = stats.total;
  const promedio = Math.round(totalAtenciones / stats.porTecnico.length);
  const periodo = "Enero - Junio 2026";

  return (
    <div className="min-h-screen bg-white p-8 print:p-4">
      {/* Boton imprimir (solo en pantalla) */}
      <div className="mb-6 flex items-center justify-between print:hidden">
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-bold text-slate-900 shadow-lg transition hover:bg-amber-400"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Imprimir / Guardar PDF
        </button>
        <p className="text-sm text-slate-400">Soporte Técnico UPDS</p>
      </div>

      <div ref={printRef} className="mx-auto max-w-4xl text-black print:text-black">
        {/* Header */}
        <div className="mb-8 border-b-2 border-amber-500 pb-4">
          <h1 className="text-3xl font-bold text-slate-900">Reporte de Desempeño</h1>
          <p className="mt-1 text-sm text-slate-500">Departamento de Sistemas — Soporte Técnico UPDS</p>
          <p className="text-sm text-slate-500">Periodo: {periodo}</p>
        </div>

        {/* Resumen ejecutivo */}
        <div className="mb-8 grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-slate-200 bg-amber-50 p-4 text-center">
            <p className="text-3xl font-bold text-amber-600">{totalAtenciones}</p>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Atenciones</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-sky-50 p-4 text-center">
            <p className="text-3xl font-bold text-sky-600">{stats.porTecnico.length}</p>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Técnicos</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-emerald-50 p-4 text-center">
            <p className="text-3xl font-bold text-emerald-600">{promedio}</p>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Promedio x Técnico</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-violet-50 p-4 text-center">
            <p className="text-3xl font-bold text-violet-600">{stats.porCategoria.length}</p>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Categorías</p>
          </div>
        </div>

        {/* Ranking */}
        <div className="mb-8">
          <h2 className="mb-3 text-lg font-bold text-slate-900">Rendimiento por Técnico</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="pb-2 pr-4">#</th>
                <th className="pb-2 pr-4">Nombre</th>
                <th className="pb-2 pr-4">Atenciones</th>
                <th className="pb-2">% del Equipo</th>
              </tr>
            </thead>
            <tbody>
              {stats.porTecnico.map((t, i) => {
                const pct = ((t.total / totalAtenciones) * 100).toFixed(1);
                return (
                  <tr key={t.usuarioId} className="border-b border-slate-100">
                    <td className="py-2 pr-4 text-slate-400">{i + 1}</td>
                    <td className="py-2 pr-4 font-medium text-slate-800">{t.displayName}</td>
                    <td className="py-2 pr-4 font-semibold text-slate-900">{t.total}</td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                          <div className="h-full rounded-full bg-amber-500" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs text-slate-500">{pct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Top categorias */}
        <div className="mb-8">
          <h2 className="mb-3 text-lg font-bold text-slate-900">Problemas más Frecuentes</h2>
          <div className="grid grid-cols-2 gap-4">
            {stats.porCategoria.map((c) => (
              <div key={c.categoria} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-700">{c.categoria}</span>
                    <span className="text-slate-500">{c.total}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
                    <div className="h-full rounded-full bg-amber-500" style={{ width: `${(c.total / maxCat) * 100}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tendencia mensual como tabla */}
        <div className="mb-8">
          <h2 className="mb-3 text-lg font-bold text-slate-900">Tendencia Mensual</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="pb-2 pr-4">Mes</th>
                <th className="pb-2 pr-4">Atenciones</th>
                <th className="pb-2">Variación</th>
              </tr>
            </thead>
            <tbody>
              {stats.porMes.map((m, i) => {
                const anterior = i > 0 ? stats.porMes[i - 1].total : m.total;
                const diff = m.total - anterior;
                const signo = diff > 0 ? "+" : diff < 0 ? "" : "=";
                const color = diff > 0 ? "text-emerald-600" : diff < 0 ? "text-red-600" : "text-slate-400";
                return (
                  <tr key={`${m.anio}-${m.mes}`} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium text-slate-800">{MONTHS[m.mes - 1]} {m.anio}</td>
                    <td className="py-2 pr-4 text-slate-700">{m.total}</td>
                    <td className={`py-2 font-semibold ${color}`}>
                      {i > 0 ? `${signo}${diff > 0 ? diff : diff < 0 ? diff : ""}` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Areas */}
        <div className="mb-8">
          <h2 className="mb-3 text-lg font-bold text-slate-900">Áreas que más solicitan Soporte</h2>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {stats.porArea.map((a) => (
              <div key={a.area} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2">
                <span className="text-slate-700">{a.area}</span>
                <span className="font-semibold text-slate-900">{a.total}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 border-t border-slate-200 pt-4 text-center text-xs text-slate-400">
          <p>Reporte generado el {new Date().toLocaleDateString("es-BO")} — Sistema de Soporte Técnico UPDS</p>
          <p>Este reporte contiene datos de {totalAtenciones} atenciones registradas por {stats.porTecnico.length} técnicos.</p>
        </div>
      </div>
    </div>
  );
}
