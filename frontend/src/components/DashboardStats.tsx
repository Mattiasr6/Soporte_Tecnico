"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getDashboardStats, getUsuarios, type DashboardStats } from "@/lib/api";
import type { Usuario } from "@/types";
import AnimatedCounter from "./AnimatedCounter";
import { SkeletonCard, SkeletonRow } from "./Skeleton";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const MONTH_OPTIONS = MONTHS.map((m, i) => ({ value: i + 1, label: m }));
const YEAR_OPTIONS = [new Date().getFullYear()];

export default function DashboardStats() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tecnicos, setTecnicos] = useState<Usuario[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [desdeMes, setDesdeMes] = useState(1);
  const [desdeAnio] = useState(new Date().getFullYear());
  const [hastaMes, setHastaMes] = useState(new Date().getMonth() + 1);
  const [expandAreas, setExpandAreas] = useState(false);

  const fetch = useCallback(async (uid?: number, dm?: number, hm?: number) => {
    try {
      const [s, u] = await Promise.all([
        getDashboardStats({
          usuarioId: uid,
          desdeMes: dm,
          desdeAnio: new Date().getFullYear(),
          hastaMes: hm,
          hastaAnio: new Date().getFullYear(),
        }),
        getUsuarios(),
      ]);
      setStats(s);
      setTecnicos(u);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(selectedUserId, desdeMes, hastaMes);
  }, [selectedUserId, desdeMes, hastaMes, fetch]);

  const exportCsv = () => {
    if (!stats) return;

    const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
    const lines: string[] = [];

    lines.push("SECCION,CLAVE,TOTAL");
    lines.push(`General,Total atenciones,${stats.total}`);
    lines.push(`Fuera de turno,${stats.fueraDeTurno}`);
    lines.push("");

    lines.push("RENDIMIENTO POR TECNICO");
    lines.push("#,,Nombre,Total");
    stats.porTecnico.forEach((t, i) => {
      lines.push(`${i + 1},,${esc(t.displayName)},${t.total}`);
    });
    lines.push("");

    lines.push("CATEGORIAS MAS FRECUENTES");
    lines.push("Categoria,Total");
    stats.porCategoria.forEach((c) => {
      lines.push(`${esc(c.categoria)},${c.total}`);
    });
    lines.push("");

    lines.push("AREAS MAS SOLICITANTES");
    lines.push("Area,Total");
    stats.porArea.forEach((a) => {
      lines.push(`${esc(a.area)},${a.total}`);
    });
    lines.push("");

    lines.push("TENDENCIA MENSUAL");
    lines.push("Anio,Mes,Total");
    stats.porMes.forEach((m) => {
      lines.push(`${m.anio},${MONTHS[m.mes - 1]},${m.total}`);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const periodo = `${MONTHS[desdeMes - 1]}-${MONTHS[hastaMes - 1]}`;
    a.download = `dashboard-stats-${periodo}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading || !stats) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <div className="space-y-3">
            {[...Array(7)].map((_, i) => <SkeletonRow key={i} />)}
          </div>
        </div>
      </div>
    );
  }

  const maxTecnico = Math.max(...stats.porTecnico.map((t) => t.total), 1);
  const maxCategoria = Math.max(...stats.porCategoria.map((c) => c.total), 1);
  const maxMes = Math.max(...stats.porMes.map((m) => m.total), 1);
  const promedio = stats.porTecnico.length > 0
    ? Math.round(stats.total / stats.porTecnico.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Filtro de periodo + export */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex items-end gap-3">
          <SelectMonth label="Desde" value={desdeMes} onChange={setDesdeMes} />
          <SelectMonth label="Hasta" value={hastaMes} onChange={setHastaMes} min={desdeMes} />
        </div>
        <div className="ml-auto flex items-center gap-3">
          <select
            value={selectedUserId ?? ""}
            onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 focus:border-amber-500/50 focus:outline-none"
          >
            <option value="">Todos</option>
            {tecnicos.map((t) => (
              <option key={t.id} value={t.id}>{t.displayName}</option>
            ))}
          </select>
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-lg transition hover:from-amber-400 hover:to-amber-500"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
            </svg>
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Cards resumen */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard label="Total Atenciones" value={stats.total} color="amber" />
        <SummaryCard label="Técnicos" value={stats.porTecnico.length} color="blue" />
        <SummaryCard label="Promedio x Técnico" value={promedio} color="emerald" />
        <SummaryCard label="Fuera de Turno" value={stats.fueraDeTurno} color="rose" />
      </div>

      {/* Ranking por tecnico */}
      <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Rendimiento por Técnico
        </h3>
        <div className="space-y-2">
          {stats.porTecnico.map((t, i) => {
            const estrellas = Math.floor(t.total / 100);
            return (
            <div key={t.usuarioId} className="flex items-center gap-3">
              <span className="w-6 text-xs font-bold text-slate-500">#{i + 1}</span>
              <button
              onClick={() => router.push(`/perfil/${t.usuarioId}`)}
              className="w-32 truncate text-left text-sm text-slate-200 transition hover:text-amber-400"
            >{t.displayName}</button>
              {estrellas > 0 && (
                <span className="flex w-16 shrink-0 gap-0.5">
                  {Array.from({ length: estrellas }).map((_, s) => (
                    <svg key={s} className="h-3.5 w-3.5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </span>
              )}
              <div className="flex-1">
                <div className="h-5 overflow-hidden rounded-full bg-slate-700">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-600 transition-all duration-500"
                    style={{ width: `${(t.total / maxTecnico) * 100}%` }}
                  />
                </div>
              </div>
              <span className="w-16 text-right text-sm font-semibold text-slate-100">{t.total}</span>
            </div>);
          })}
        </div>
      </section>

      {/* Categorias — Donut + Barras */}
      <div className="grid gap-6 lg:grid-cols-5">
        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5 lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Distribución</h3>
          <DonutChart data={stats.porCategoria.map((c) => ({ label: c.categoria, value: c.total }))} />
        </section>
        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5 lg:col-span-3">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Categorías más frecuentes</h3>
          <div className="space-y-2">
            {stats.porCategoria.map((c) => (
              <div key={c.categoria} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">{c.categoria}</span>
                    <span className="text-slate-400">{c.total}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-600 transition-all duration-500"
                      style={{ width: `${(c.total / maxCategoria) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Areas y Tendencia */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Áreas más solicitantes</h3>
            <button onClick={() => setExpandAreas(!expandAreas)}
              className="text-xs text-amber-400 hover:text-amber-300 transition">
              {expandAreas ? "Ver menos" : `Ver todas (${stats.porArea.length})`}
            </button>
          </div>
          <div className="space-y-2">
            {(expandAreas ? stats.porArea : stats.porArea.slice(0, 8)).map((a) => (
              <div key={a.area} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">{a.area}</span>
                    <span className="text-slate-400">{a.total}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-500 to-violet-600 transition-all duration-500"
                      style={{ width: `${(a.total / Math.max(...stats.porArea.map((x) => x.total), 1)) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Tendencia Mensual</h3>
          <LineChart data={stats.porMes.map((m) => ({ label: MONTHS[m.mes - 1], value: m.total }))} />
        </section>
      </div>
    </div>
  );
}

const COLORS = ["#f59e0b","#10b981","#3b82f6","#8b5cf6","#ec4899","#14b8a6","#f97316","#e11d48","#84cc16","#06b6d4"];

function DonutChart({ data }: { data: { label: string; value: number }[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <p className="py-8 text-center text-xs text-slate-500">Sin datos</p>;
  const r = 80;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  const slices = data.map((d, i) => {
    const slice = (d.value / total) * circ;
    const start = offset;
    offset += slice;
    return { ...d, slice, start, color: COLORS[i % COLORS.length] };
  });

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="200" viewBox="0 0 200 200">
        {slices.map((s, i) => (
          <circle
            key={i}
            cx="100" cy="100" r={r}
            fill="none"
            stroke={s.color}
            strokeWidth="32"
            strokeDasharray={`${s.slice} ${circ - s.slice}`}
            strokeDashoffset={-s.start}
            transform="rotate(-90 100 100)"
            className="transition-all duration-700"
          />
        ))}
        <circle cx="100" cy="100" r="50" fill="#1e293b" />
        <text x="100" y="96" textAnchor="middle" className="fill-slate-100 text-2xl font-bold">{total}</text>
        <text x="100" y="114" textAnchor="middle" className="fill-slate-500 text-[10px]">atenciones</text>
      </svg>
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
        {slices.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-slate-300 truncate max-w-24">{s.label}</span>
            <span className="text-slate-500">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LineChart({ data }: { data: { label: string; value: number }[] }) {
  if (data.length === 0) return <p className="py-8 text-center text-xs text-slate-500">Sin datos</p>;

  const w = 500, h = 160, px = 40, py = 20;
  const max = Math.max(...data.map((d) => d.value), 1);
  const xStep = (w - px * 2) / (data.length - 1 || 1);

  const points = data.map((d, i) => `${px + i * xStep},${h - py - ((d.value / max) * (h - py * 2))}`).join(" ");
  const areaPoints = `${px},${h - py} ${points} ${px + (data.length - 1) * xStep},${h - py}`;

  return (
    <div className="flex justify-center">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-md" style={{ height: "180px" }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((r, i) => (
          <line key={i} x1={px} y1={h - py - r * (h - py * 2)} x2={w - px} y2={h - py - r * (h - py * 2)}
            stroke="#334155" strokeWidth="1" strokeDasharray="4 4" />
        ))}
        {/* Area fill */}
        <polygon points={areaPoints} fill="url(#lineGrad)" opacity="0.2" />
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Line */}
        <polyline points={points} fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" className="transition-all duration-700" />
        {/* Dots */}
        {data.map((d, i) => (
          <circle key={i} cx={px + i * xStep} cy={h - py - ((d.value / max) * (h - py * 2))} r="4" fill="#f59e0b" stroke="#1e293b" strokeWidth="2" />
        ))}
        {/* Labels */}
        {data.map((d, i) => (
          <text key={i} x={px + i * xStep} y={h - 4} textAnchor="middle" className="fill-slate-500 text-[10px]">{d.label}</text>
        ))}
      </svg>
    </div>
  );
}

function SelectMonth({ label, value, onChange, min }: { label: string; value: number; onChange: (v: number) => void; min?: number }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 focus:border-amber-500/50 focus:outline-none"
      >
        {MONTH_OPTIONS.filter((m) => !min || m.value >= min).map((m) => (
          <option key={m.value} value={m.value}>{m.label}</option>
        ))}
      </select>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    amber: "border-amber-500/30 from-amber-500/10 to-transparent text-amber-400",
    blue: "border-sky-500/30 from-sky-500/10 to-transparent text-sky-400",
    emerald: "border-emerald-500/30 from-emerald-500/10 to-transparent text-emerald-400",
    rose: "border-rose-500/30 from-rose-500/10 to-transparent text-rose-400",
    orange: "border-orange-500/30 from-orange-500/10 to-transparent text-orange-400",
    violet: "border-violet-500/30 from-violet-500/10 to-transparent text-violet-400",
  };

  return (
    <div className={`rounded-xl border bg-gradient-to-br p-4 ${colors[color] ?? colors.amber}`}>
      <p className="text-xs font-medium uppercase tracking-wider opacity-70">{label}</p>
      <p className="mt-1 text-2xl font-bold">
        <AnimatedCounter value={value} />
      </p>
    </div>
  );
}
