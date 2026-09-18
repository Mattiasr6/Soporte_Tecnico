"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { getAtenciones, getUsuarios } from "@/lib/api";
import type { AtencionItem, Usuario } from "@/types";
import { useSignalR } from "@/lib/SignalRProvider";

const C = {
  house: "#1e3932",
  accent: "#00754A",
  starbucks: "#006241",
  gold: "#cba258",
  cream: "#faf6ee",
  surface: "#ffffff",
  border: "#e7e7e7",
  muted: "rgba(0,0,0,.58)",
} as const;

const PADRE_COLORS: Record<string, string> = {
  Administrativos: C.house,
  Académicos: C.accent,
  Extras: C.starbucks,
};

const pct = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);

interface Filters {
  padre: string;
  grupo: string;
  area: string;
  tecnicoId: string;
  fuera: "" | "fuera" | "en";
}

const EMPTY: Filters = { padre: "", grupo: "", area: "", tecnicoId: "", fuera: "" };

const gp = (a: AtencionItem) => a.grupoPadreNombre || "Sin grupo";
const gr = (a: AtencionItem) => a.grupoNombre || "Directo";
const ar = (a: AtencionItem) => a.areaNombre || a.areaSolicitante;

export default function DashboardCardsV2() {
  const [atenciones, setAtenciones] = useState<AtencionItem[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const { lastStatus } = useSignalR();

  useEffect(() => {
    Promise.all([getAtenciones(), getUsuarios()])
      .then(([a, u]) => { setAtenciones(a); setUsuarios(u); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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

  /* ── cascading filter options ── */
  const jerarquia = useMemo(() => {
    const padres = new Map<string, Map<string, Set<string>>>();
    const allAreas: { id: string; nombre: string; grupoPadre: string; grupo: string }[] = [];

    atenciones.forEach((a) => {
      const p = gp(a), g = gr(a), area = ar(a);
      if (!padres.has(p)) padres.set(p, new Map());
      const grupos = padres.get(p)!;
      if (!grupos.has(g)) grupos.set(g, new Set());
      grupos.get(g)!.add(area);
      if (!allAreas.find((x) => x.nombre === area)) {
        allAreas.push({ id: area, nombre: area, grupoPadre: p, grupo: g });
      }
    });

    return { padres, allAreas };
  }, [atenciones]);

  const padreOptions = useMemo(() => [...jerarquia.padres.keys()].sort(), [jerarquia]);

  const grupoOptions = useMemo(() => {
    if (!filters.padre) return [];
    return [...(jerarquia.padres.get(filters.padre)?.keys() || [])].sort();
  }, [filters.padre, jerarquia]);

  const areaOptions = useMemo(() => {
    if (filters.padre && filters.grupo) {
      const areas = jerarquia.padres.get(filters.padre)?.get(filters.grupo);
      return areas ? [...areas].sort() : [];
    }
    if (filters.padre) {
      const grupos = jerarquia.padres.get(filters.padre);
      if (!grupos) return [];
      const areas = new Set<string>();
      grupos.forEach((arSet) => arSet.forEach((a) => areas.add(a)));
      return [...areas].sort();
    }
    return jerarquia.allAreas.map((a) => a.nombre).sort();
  }, [filters.padre, filters.grupo, jerarquia]);

  const tecnicoOptions = useMemo(() => usuarios.filter((u) => u.role === "Tecnico"), [usuarios]);

  /* ── filtered data ── */
  const filtered = useMemo(() => {
    let result = atenciones;
    if (filters.padre) result = result.filter((a) => gp(a) === filters.padre);
    if (filters.grupo) result = result.filter((a) => gr(a) === filters.grupo);
    if (filters.area) result = result.filter((a) => ar(a) === filters.area);
    if (filters.tecnicoId) result = result.filter((a) => String(a.usuarioId) === filters.tecnicoId);
    if (filters.fuera === "fuera") result = result.filter((a) => a.fueraDeTurno);
    if (filters.fuera === "en") result = result.filter((a) => !a.fueraDeTurno);
    return result;
  }, [atenciones, filters]);

  /* ── KPI computations ── */
  const kpis = useMemo(() => {
    const total = filtered.length;
    const fuera = filtered.filter((a) => a.fueraDeTurno).length;

    const byPadre = padreOptions.map((nombre) => ({
      nombre,
      count: filtered.filter((a) => gp(a) === nombre).length,
    }));
    const topPadre = [...byPadre].sort((a, b) => b.count - a.count)[0];

    return { total, fuera, byPadre, topPadre };
  }, [filtered, padreOptions]);

  /* ── donut conic-gradient ── */
  const donutGrad = useMemo(() => {
    let acc = 0;
    return kpis.byPadre
      .map((p) => {
        const pctVal = pct(p.count, kpis.total);
        const s = acc;
        acc += pctVal;
        return `${PADRE_COLORS[p.nombre] || "#d6dbde"} ${s}% ${acc}%`;
      })
      .join(", ") || `${C.accent} 0% 100%`;
  }, [kpis]);

  const setFilter = useCallback(<K extends keyof Filters>(key: K, val: Filters[K]) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: val };
      if (key === "padre") { next.grupo = ""; next.area = ""; }
      if (key === "grupo") { next.area = ""; }
      return next;
    });
  }, []);

  const clearAll = useCallback(() => setFilters(EMPTY), []);

  const activeChips: { key: string; label: string; reset: () => void }[] = [
    filters.padre && { key: "padre", label: filters.padre, reset: () => setFilter("padre", "") },
    filters.grupo && { key: "grupo", label: filters.grupo, reset: () => setFilter("grupo", "") },
    filters.area && { key: "area", label: filters.area, reset: () => setFilter("area", "") },
    filters.tecnicoId && { key: "tecnicoId", label: tecnicoOptions.find((t) => String(t.id) === filters.tecnicoId)?.displayName || filters.tecnicoId, reset: () => setFilter("tecnicoId", "") },
    filters.fuera && { key: "fuera", label: filters.fuera === "fuera" ? "Fuera turno" : "En turno", reset: () => setFilter("fuera", "") },
  ].filter(Boolean) as { key: string; label: string; reset: () => void }[];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3" style={{ color: "#1e3932" }}>
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Cargando datos jerárquicos...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Header band ── */}
      <div className="rounded-xl p-5 text-white" style={{ background: C.house }}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-[11px] font-bold uppercase tracking-widest opacity-60">
              Dashboard · KPIs jerárquicos
            </p>
            <h1 className="text-xl font-bold lg:text-2xl">
              Operación visible por jerarquía —<br className="hidden lg:block" /> de GrupoPadre a Área.
            </h1>
            <p className="mt-2 max-w-[720px] text-sm opacity-72">
              KPIs por GrupoPadre y por Área jerárquica con filtros en cascada (Padre → Grupo → Área).
            </p>
          </div>
          <div className="min-w-[240px] rounded-xl bg-white p-3" style={{ color: C.house }}>
            <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>
              Ventana filtrada
            </p>
            <p className="mt-1 text-sm font-bold">
              {kpis.total} atenciones · {kpis.total ? `~${Math.round(kpis.total / 30)}/día` : "0/día"}
            </p>
            <div className="mt-2 flex gap-1.5">
              <span className="rounded-full px-2.5 py-0.5 text-[11px] font-bold text-white" style={{ background: C.house }}>
                {kpis.total} atenciones
              </span>
              <span className="rounded-full border px-2.5 py-0.5 text-[11px]" style={{ borderColor: "#f0ede8", color: "#1e3932" }}>
                {kpis.fuera} fuera turno
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className="rounded-xl border bg-white p-3.5 shadow-sm" style={{ borderColor: C.border }}>
        <div className="flex flex-wrap gap-2.5">
          <label className="flex min-w-[160px] flex-1 flex-col gap-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Grupo Padre</span>
            <select className="rounded border-[1.5px] px-2.5 py-2 text-[13px] font-medium outline-none transition-colors focus:border-[#00754A] focus:ring-2 focus:ring-[#00754A]/20 hover:border-[#00754A]/50" style={{ borderColor: C.border, color: "#1e3932" }} value={filters.padre} onChange={(e) => setFilter("padre", e.target.value)}>
              <option value="">Todos ({padreOptions.length})</option>
              {padreOptions.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
          <label className="flex min-w-[160px] flex-1 flex-col gap-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Grupo</span>
            <select className="rounded border-[1.5px] px-2.5 py-2 text-[13px] font-medium outline-none transition-colors focus:border-[#00754A] focus:ring-2 focus:ring-[#00754A]/20 hover:border-[#00754A]/50" style={{ borderColor: C.border, color: "#1e3932" }} value={filters.grupo} onChange={(e) => setFilter("grupo", e.target.value)}>
              <option value="">{filters.padre ? `Todos (${grupoOptions.length})` : "Elige Padre"}</option>
              {grupoOptions.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label className="flex min-w-[160px] flex-1 flex-col gap-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Área ({areaOptions.length})</span>
            <select className="rounded border-[1.5px] px-2.5 py-2 text-[13px] font-medium outline-none transition-colors focus:border-[#00754A] focus:ring-2 focus:ring-[#00754A]/20 hover:border-[#00754A]/50" style={{ borderColor: C.border, color: "#1e3932" }} value={filters.area} onChange={(e) => setFilter("area", e.target.value)}>
              <option value="">Todas</option>
              {areaOptions.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
          <label className="flex min-w-[140px] flex-col gap-1.5" style={{ flex: "0 0 160px" }}>
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Técnico</span>
            <select className="rounded border-[1.5px] px-2.5 py-2 text-[13px] font-medium outline-none transition-colors focus:border-[#00754A] focus:ring-2 focus:ring-[#00754A]/20 hover:border-[#00754A]/50" style={{ borderColor: C.border, color: "#1e3932" }} value={filters.tecnicoId} onChange={(e) => setFilter("tecnicoId", e.target.value)}>
              <option value="">Todos</option>
              {tecnicoOptions.map((t) => <option key={t.id} value={String(t.id)}>{t.displayName}</option>)}
            </select>
          </label>
          <label className="flex min-w-[120px] flex-col gap-1.5" style={{ flex: "0 0 140px" }}>
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Fuera de turno</span>
            <select className="rounded border-[1.5px] px-2.5 py-2 text-[13px] font-medium outline-none transition-colors focus:border-[#00754A] focus:ring-2 focus:ring-[#00754A]/20 hover:border-[#00754A]/50" style={{ borderColor: C.border, color: "#1e3932" }} value={filters.fuera} onChange={(e) => setFilter("fuera", e.target.value as Filters["fuera"])}>
              <option value="">Todos</option>
              <option value="fuera">Solo fuera</option>
              <option value="en">Solo en turno</option>
            </select>
          </label>
        </div>

        {activeChips.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3" style={{ borderColor: "#f0ede8" }}>
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Filtros activos</span>
            {activeChips.map((chip) => (
              <button
                key={chip.key}
                onClick={chip.reset}
                className="rounded-full border-[1.5px] px-3 py-1 text-xs font-semibold transition hover:opacity-80"
                style={{
                  background: chip.key === "area" ? C.house : C.accent,
                  color: "#fff",
                  borderColor: chip.key === "area" ? C.house : C.accent,
                }}
              >
                {chip.label} ×
              </button>
            ))}
            <button
              onClick={clearAll}
              className="rounded-full border px-3 py-1 text-xs font-semibold"
              style={{ color: "#1e3932", borderColor: C.border }}
            >
              Limpiar
            </button>
          </div>
        )}
      </div>

      {/* ── KPI Grid ── */}
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard dark label="Total atenciones" value={String(kpis.total)} sub={`${kpis.total ? `~${Math.round(kpis.total / 30)}/día` : "0/día"}`} />
        <KpiCard
          label="Share por GrupoPadre"
          value={kpis.byPadre.map((p) => `${p.nombre} ${pct(p.count, kpis.total)}%`).join(" · ")}
          valueSize="text-[22px]"
          sub={`${kpis.byPadre.length} padres · top ${kpis.topPadre?.nombre} ${kpis.topPadre?.count}`}
        />
        <KpiCard
          label="Fuera de turno"
          value={`${pct(kpis.fuera, kpis.total)}%`}
          valueSuffix={` · ${kpis.fuera} casos`}
          sub=""
        />
        <KpiCard
          label="Tiempo medio cierre"
          value="3.2h"
          valueSuffix=" · SLA 4h"
          badge={{ text: "81% dentro SLA", bg: "#fff7e0", color: "#7a5a00", border: "#f0d9a0" }}
        />
      </div>

      {/* ── Donut + Padre bars ── */}
      <div className="rounded-xl border bg-white shadow-sm" style={{ borderColor: C.border }}>
        <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "#f0ede8" }}>
          <h3 className="text-sm font-bold" style={{ color: C.house }}>KPIs por GrupoPadre</h3>
          <small className="text-xs" style={{ color: "#1e3932" }}>{kpis.byPadre.length} bloques · share + volumen</small>
        </div>
        <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
          <div className="relative grid h-[120px] w-[120px] shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(${donutGrad})` }}>
            <div className="absolute h-[72px] w-[72px] rounded-full bg-white" />
            <div className="relative z-10 text-center">
              <strong className="text-lg" style={{ color: C.house }}>{kpis.total}</strong>
              <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Total</div>
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-2">
            {kpis.byPadre.map((p) => (
              <div key={p.nombre} className="flex items-center gap-3">
                <span className="flex shrink-0 items-center gap-2 text-xs" style={{ color: "#1e3932" }}>
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: PADRE_COLORS[p.nombre] || "#d6dbde" }} />
                  {p.nombre}
                </span>
                <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: C.cream }}>
                  <div className="h-full rounded-full" style={{ width: `${pct(p.count, kpis.total)}%`, background: PADRE_COLORS[p.nombre] || "#d6dbde" }} />
                </div>
                <span className="w-16 text-right text-xs font-bold" style={{ color: C.house }}>
                  {pct(p.count, kpis.total)}% · {p.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  dark, label, value, valueSize, valueSuffix, sub, badge,
}: {
  dark?: boolean;
  label: string;
  value: string;
  valueSize?: string;
  valueSuffix?: string;
  sub?: string;
  badge?: { text: string; bg: string; color: string; border: string };
}) {
  const bg = dark ? C.house : C.surface;
  const fg = dark ? "#fff" : C.house;
  const mutedFg = dark ? "rgba(255,255,255,.6)" : C.muted;

  return (
    <div className="rounded-xl p-4 shadow-sm" style={{ background: bg, color: fg, border: `1px solid ${dark ? C.house : C.border}` }}>
      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: mutedFg }}>{label}</p>
      <p className={`mt-1.5 font-extrabold tracking-tight ${valueSize || "text-[28px]"}`}>
        {value}
        {valueSuffix && <span className="ml-1 text-[13px] font-medium" style={{ color: mutedFg }}>{valueSuffix}</span>}
      </p>
      {sub && <p className="mt-1 text-xs" style={{ color: mutedFg }}>{sub}</p>}
      {badge && (
        <p className="mt-1 text-xs">
          <span className="rounded-full px-2 py-0.5 text-[11px] font-bold" style={{ background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}>
            {badge.text}
          </span>
        </p>
      )}
      <SparkBars dark={dark} />
    </div>
  );
}

function SparkBars({ dark }: { dark?: boolean }) {
  const bars = [0.4, 0.7, 0.3, 0.5, 0.6].map((h) => ({
    h: `${20 + h * 60}%`,
    on: Math.random() > 0.4,
  }));

  return (
    <div className="mt-2.5 flex h-7 items-end gap-[3px]">
      {bars.map((b, i) => (
        <div
          key={i}
          className="flex-1 rounded-t"
          style={{
            height: b.h,
            background: dark
              ? b.on ? C.gold : "rgba(255,255,255,.15)"
              : b.on ? C.accent : "#edebe9",
          }}
        />
      ))}
    </div>
  );
}
