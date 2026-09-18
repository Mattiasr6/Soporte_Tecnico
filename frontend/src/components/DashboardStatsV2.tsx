"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { getAtenciones, getUsuarios } from "@/lib/api";
import type { AtencionItem, Usuario } from "@/types";

const C = {
  house: "#1e3932",
  accent: "#00754A",
  starbucks: "#006241",
  gold: "#cba258",
  cream: "#faf6ee",
  border: "#e7e7e7",
  muted: "rgba(0,0,0,.58)",
} as const;

const PADRE_COLORS: Record<string, string> = {
  Administrativos: C.house,
  Académicos: C.accent,
  Extras: C.starbucks,
};

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

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
const pct = (n: number, t: number) => (t ? Math.round((n / t) * 100) : 0);

export default function DashboardStatsV2() {
  const [atenciones, setAtenciones] = useState<AtencionItem[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [expandAll, setExpandAll] = useState(false);

  useEffect(() => {
    Promise.all([getAtenciones(), getUsuarios()])
      .then(([a, u]) => { setAtenciones(a); setUsuarios(u); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const jerarquia = useMemo(() => {
    const padres = new Map<string, Map<string, Set<string>>>();
    const allAreas: { nombre: string; grupoPadre: string; grupo: string }[] = [];
    atenciones.forEach((a) => {
      const p = gp(a), g = gr(a), area = ar(a);
      if (!padres.has(p)) padres.set(p, new Map());
      const grupos = padres.get(p)!;
      if (!grupos.has(g)) grupos.set(g, new Set());
      grupos.get(g)!.add(area);
      if (!allAreas.find((x) => x.nombre === area)) allAreas.push({ nombre: area, grupoPadre: p, grupo: g });
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

  const filtered = useMemo(() => {
    let r = atenciones;
    if (filters.padre) r = r.filter((a) => gp(a) === filters.padre);
    if (filters.grupo) r = r.filter((a) => gr(a) === filters.grupo);
    if (filters.area) r = r.filter((a) => ar(a) === filters.area);
    if (filters.tecnicoId) r = r.filter((a) => String(a.usuarioId) === filters.tecnicoId);
    if (filters.fuera === "fuera") r = r.filter((a) => a.fueraDeTurno);
    if (filters.fuera === "en") r = r.filter((a) => !a.fueraDeTurno);
    return r;
  }, [atenciones, filters]);

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
    filters.tecnicoId && { key: "tecnicoId", label: tecnicoOptions.find((t) => String(t.id) === filters.tecnicoId)?.displayName || "", reset: () => setFilter("tecnicoId", "") },
    filters.fuera && { key: "fuera", label: filters.fuera === "fuera" ? "Fuera turno" : "En turno", reset: () => setFilter("fuera", "") },
  ].filter(Boolean) as { key: string; label: string; reset: () => void }[];

  const hierGroups = useMemo(() => {
    const grouped: Record<string, { padre: string; grupo: string; count: number; areas: Record<string, number> }> = {};
    filtered.forEach((a) => {
      const key = `${gp(a)}|${gr(a)}`;
      if (!grouped[key]) grouped[key] = { padre: gp(a), grupo: gr(a), count: 0, areas: {} };
      grouped[key].count++;
      grouped[key].areas[ar(a)] = (grouped[key].areas[ar(a)] || 0) + 1;
    });
    return Object.values(grouped).sort((a, b) => b.count - a.count);
  }, [filtered]);

  const topAreas = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((a) => { counts[ar(a)] = (counts[ar(a)] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [filtered]);

  const porTecnico = useMemo(() => {
    const counts: Record<number, number> = {};
    filtered.forEach((a) => { counts[a.usuarioId] = (counts[a.usuarioId] || 0) + 1; });
    return Object.entries(counts)
      .map(([uid, total]) => ({ id: Number(uid), name: usuarios.find((x) => x.id === Number(uid))?.displayName || `#${uid}`, total }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 8);
  }, [filtered, usuarios]);

  const porMes = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((a) => {
      const d = new Date(a.createdAt);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([key, total]) => ({ key, year: +key.slice(0, 4), month: +key.slice(5, 7), total }))
      .sort((a, b) => a.year - b.year || a.month - b.month)
      .slice(-12);
  }, [filtered]);

  const categorias = useMemo(() => {
    const counts: Record<string, number> = {};
    filtered.forEach((a) => { counts[a.categoria] = (counts[a.categoria] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [filtered]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3" style={{ color: "#1e3932" }}>
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Cargando estadísticas...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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
              <button key={chip.key} onClick={chip.reset} className="rounded-full border-[1.5px] px-3 py-1 text-xs font-semibold text-white" style={{ background: chip.key === "area" ? C.house : C.accent, borderColor: chip.key === "area" ? C.house : C.accent }}>
                {chip.label} ×
              </button>
            ))}
            <button onClick={clearAll} className="rounded-full border px-3 py-1 text-xs font-semibold" style={{ color: "#1e3932", borderColor: C.border }}>Limpiar</button>
          </div>
        )}
      </div>

      {/* ── 3-panel grid (343px) ── */}
      <div className="grid grid-cols-1 gap-4 md:gap-5 lg:grid-cols-3 lg:gap-6">
        <Panel title="Por Área jerárquica" subtitle={`Drill-down · ${hierGroups.length} grupos`}>
          <div className="flex gap-3 px-3.5 pt-2 text-[11px]" style={{ color: "#1e3932" }}>
            <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: C.house }} /> Padre</span>
            <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: C.accent }} /> Grupo</span>
            <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: C.gold }} /> Área</span>
          </div>
          <div className="flex flex-col gap-2 p-3.5">
            {hierGroups.length === 0 ? (
              <p className="py-4 text-center text-xs" style={{ color: "#1e3932" }}>Sin datos — ajusta filtros</p>
            ) : (
              hierGroups.slice(0, expandAll ? undefined : 4).map((g) => (
                <HierGroup key={`${g.padre}|${g.grupo}`} g={g} active={filters.padre === g.padre} />
              ))
            )}
          </div>
          {hierGroups.length > 4 && (
            <button onClick={() => setExpandAll(!expandAll)} className="w-full border-t py-2.5 text-center text-xs font-semibold" style={{ borderColor: "#f0ede8", color: "#1e3932", background: C.cream }}>
              {expandAll ? "Contraer" : `Expandir todo (${hierGroups.length})`}
            </button>
          )}
        </Panel>

        <Panel title="Top Áreas (volumen)" subtitle="Filtrado por jerarquía activa">
          <div className="flex flex-col gap-2.5 px-4 py-3.5">
            {topAreas.length === 0 ? (
              <p className="py-4 text-center text-xs" style={{ color: "#1e3932" }}>Sin áreas</p>
            ) : (
              topAreas.map(([name, count]) => {
                const aData = jerarquia.allAreas.find((a) => a.nombre === name);
                const col = aData?.grupoPadre === "Administrativos" ? C.house : aData?.grupoPadre === "Académicos" ? C.accent : C.gold;
                const maxCount = topAreas[0][1];
                return (
                  <div key={name}>
                    <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "#1e3932" }}>
                      <span>{name} <small className="font-medium" style={{ color: "#1e3932" }}>{aData?.grupoPadre}{aData?.grupo ? ` › ${aData.grupo}` : ""}</small></span>
                      <span className="font-bold" style={{ color: C.house }}>{count}</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full" style={{ background: C.cream }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.round((count / maxCount) * 100)}%`, background: col }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
          {categorias.length > 0 && (
            <div className="border-t px-4 py-3" style={{ borderColor: "#f0ede8" }}>
              <p className="mb-2 text-[11px] font-bold uppercase tracking-wider" style={{ color: "#1e3932" }}>Por categoría ({categorias.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {categorias.map(([cat, count]) => (
                  <span
                    key={cat}
                    className="rounded-full border px-2.5 py-1 text-[11px] font-semibold"
                    style={{
                      background: cat === "Red / Internet" ? C.accent : "#fff",
                      color: cat === "Red / Internet" ? "#fff" : C.muted,
                      borderColor: cat === "Red / Internet" ? C.accent : C.border,
                    }}
                  >
                    {cat} {pct(count, filtered.length)}%
                  </span>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Por Técnico" subtitle={`${porTecnico.length} técnicos`}>
          <div className="flex flex-col gap-2.5 px-4 py-3.5">
            {porTecnico.length === 0 ? (
              <p className="py-4 text-center text-xs" style={{ color: "#1e3932" }}>Sin técnicos</p>
            ) : (
              porTecnico.map((t) => {
                const maxCount = porTecnico[0].total;
                return (
                  <div key={t.id}>
                    <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "#1e3932" }}>
                      <span>{t.name}</span>
                      <span className="font-bold" style={{ color: C.house }}>{t.total}</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full" style={{ background: C.cream }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.round((t.total / maxCount) * 100)}%`, background: C.accent }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Panel>
      </div>

      {/* ── porMes line chart ── */}
      <Panel title="Tendencia mensual" subtitle={`${porMes.length} meses`}>
        <div className="px-4 py-4">
          {porMes.length === 0 ? (
            <p className="py-4 text-center text-xs" style={{ color: "#1e3932" }}>Sin datos mensuales</p>
          ) : (
            <LineChart data={porMes} />
          )}
        </div>
      </Panel>

      {/* ── Detail table ── */}
      <Panel title="Detalle operativo — últimas atenciones" subtitle={`${filtered.length} filas`}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b" style={{ borderColor: "#f0ede8" }}>
                {["ID", "Jerarquía", "Solicitante", "Categoría", "Medio", "Fuera turno"].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider" style={{ color: "#1e3932", background: C.cream }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={6} className="px-3 py-6 text-center" style={{ color: "#1e3932" }}>Sin filas — ajusta filtros</td></tr>
              ) : (
                filtered.slice(0, 10).map((a) => (
                  <tr key={a.id} className="border-b" style={{ borderColor: "#f5f3f0" }}>
                    <td className="px-3 py-2.5 font-semibold" style={{ color: "#1e3932" }}>{a.id}</td>
                    <td className="px-3 py-2.5" style={{ color: "#1e3932" }}>{gp(a)} › {gr(a)} › {ar(a)}</td>
                    <td className="px-3 py-2.5">
                      <span className="rounded-full px-2 py-0.5 text-[11px] font-bold text-white" style={{ background: C.house }}>{a.usuarioSolicitante}</span>
                    </td>
                    <td className="px-3 py-2.5" style={{ color: "#1e3932" }}>{a.categoria}</td>
                    <td className="px-3 py-2.5" style={{ color: "#1e3932" }}>{a.medioSolicitud}</td>
                    <td className="px-3 py-2.5" style={{ color: "#1e3932" }}>
                      {a.fueraDeTurno ? (
                        <span className="rounded-full px-2 py-0.5 text-[11px] font-bold" style={{ background: "#fff7e0", color: "#7a5a00", border: "1px solid #f0d9a0" }}>
                          Sí · {new Date(a.createdAt).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {filtered.length > 10 && (
          <div className="border-t px-3.5 py-2.5 text-[11px]" style={{ borderColor: "#f0ede8", color: "#1e3932", background: C.cream }}>
            Mostrando 10 de {filtered.length} filas
          </div>
        )}
      </Panel>
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border bg-white shadow-sm" style={{ borderColor: C.border }}>
      <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "#f0ede8" }}>
        <h3 className="text-sm font-bold" style={{ color: C.house }}>{title}</h3>
        {subtitle && <small style={{ color: "#1e3932" }}>{subtitle}</small>}
      </div>
      {children}
    </div>
  );
}

function HierGroup({ g, active }: { g: { padre: string; grupo: string; count: number; areas: Record<string, number> }; active: boolean }) {
  const [open, setOpen] = useState(false);
  const areaEntries = Object.entries(g.areas).sort((a, b) => b[1] - a[1]);
  const maxArea = Math.max(...areaEntries.map((x) => x[1]), 1);

  return (
    <div className="overflow-hidden rounded-xl border" style={{ borderColor: active ? C.accent : "#f0ede8", background: C.cream }}>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2.5 text-left"
        style={{ background: active ? "#f0faf6" : undefined }}
      >
        <strong className="text-[13px]" style={{ color: C.house }}>{g.padre} · {g.grupo}</strong>
        <span className="rounded-full border px-2 py-0.5 text-[11px]" style={{ borderColor: C.border, color: "#1e3932", background: "#fff" }}>
          {g.count}
        </span>
      </button>
      {(open || areaEntries.length <= 3) && (
        <div className="flex flex-col gap-1.5 px-3 pb-2.5">
          {areaEntries.slice(0, open ? undefined : 3).map(([name, count]) => (
            <div key={name} className="flex items-center justify-between rounded-lg border bg-white px-2.5 py-1.5 text-xs" style={{ borderColor: C.border }}>
              <strong className="font-semibold" style={{ color: "#1e3932" }}>{name}</strong>
              <div className="mx-2.5 h-1 flex-1 overflow-hidden rounded-full" style={{ background: C.cream }}>
                <div className="h-full rounded-full" style={{ width: `${Math.round((count / maxArea) * 100)}%`, background: C.accent }} />
              </div>
              <span className="font-bold" style={{ color: C.house }}>{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LineChart({ data }: { data: { key: string; month: number; total: number }[] }) {
  const max = Math.max(...data.map((d) => d.total), 1);
  const h = 120;
  const pad = 20;

  const points = data.map((d, i) => ({
    x: data.length === 1 ? 50 : (i / (data.length - 1)) * 100,
    y: h - pad - (d.total / max) * (h - pad * 2),
  }));

  const toSvg = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"} ${(p.x / 100) * 800} ${p.y}`).join(" ");

  const linePath = toSvg(points);
  const areaPath = `${linePath} L ${(points[points.length - 1]?.x || 0) / 100 * 800} ${h - pad} L ${points[0] ? (points[0].x / 100) * 800 : 0} ${h - pad} Z`;

  return (
    <div className="relative" style={{ height: h + 30 }}>
      <svg viewBox={`0 0 800 ${h}`} preserveAspectRatio="none" className="w-full" style={{ height: h }}>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <line key={f} x1="0" y1={h - pad - f * (h - pad * 2)} x2="800" y2={h - pad - f * (h - pad * 2)} stroke="#f0ede8" strokeWidth="0.5" />
        ))}
        <path d={areaPath} fill={C.accent} fillOpacity="0.1" />
        <path d={linePath} fill="none" stroke={C.accent} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={(p.x / 100) * 800} cy={p.y} r="3.5" fill="#fff" stroke={C.accent} strokeWidth="2" />
        ))}
      </svg>
      <div className="flex justify-between px-1 text-[10px]" style={{ color: "#1e3932" }}>
        {data.map((d) => <span key={d.key}>{MONTHS[d.month - 1]}</span>)}
      </div>
    </div>
  );
}
