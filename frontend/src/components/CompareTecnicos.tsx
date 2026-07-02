"use client";

import { useEffect, useState } from "react";
import { getDashboardStats, getUsuarios, type DashboardStats } from "@/lib/api";
import type { Usuario } from "@/types";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function CompareTecnicos() {
  const [tecnicos, setTecnicos] = useState<Usuario[]>([]);
  const [id1, setId1] = useState<number | null>(null);
  const [id2, setId2] = useState<number | null>(null);
  const [s1, setS1] = useState<DashboardStats | null>(null);
  const [s2, setS2] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getUsuarios().then((u) => {
      setTecnicos(u);
      if (u.length >= 2) {
        setId1(u[0].id);
        setId2(u[1].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!id1 || !id2) return;
    setLoading(true);
    Promise.all([
      getDashboardStats({ usuarioId: id1 }),
      getDashboardStats({ usuarioId: id2 }),
    ]).then(([a, b]) => {
      setS1(a);
      setS2(b);
    }).finally(() => setLoading(false));
  }, [id1, id2]);

  const name1 = tecnicos.find((t) => t.id === id1)?.displayName ?? "";
  const name2 = tecnicos.find((t) => t.id === id2)?.displayName ?? "";

  // Merge de categorias de ambos lados
  const allCats = [...new Set([
    ...(s1?.porCategoria ?? []).map((c) => c.categoria),
    ...(s2?.porCategoria ?? []).map((c) => c.categoria),
  ])];

  const maxCat = Math.max(
    ...allCats.map((cat) => Math.max(
      s1?.porCategoria.find((c) => c.categoria === cat)?.total ?? 0,
      s2?.porCategoria.find((c) => c.categoria === cat)?.total ?? 0,
    )), 1,
  );

  // Merge de meses
  const allMeses = [...new Set([
    ...(s1?.porMes ?? []).map((m) => `${m.anio}-${m.mes}`),
    ...(s2?.porMes ?? []).map((m) => `${m.anio}-${m.mes}`),
  ])].sort();

  const maxMes = Math.max(
    ...allMeses.map((key) => Math.max(
      s1?.porMes.find((m) => `${m.anio}-${m.mes}` === key)?.total ?? 0,
      s2?.porMes.find((m) => `${m.anio}-${m.mes}` === key)?.total ?? 0,
    )), 1,
  );

  return (
    <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Comparación 1 a 1
      </h3>

      {/* Selectores */}
      <div className="mb-6 grid grid-cols-2 gap-4">
        <SelectTecnico
          label="Técnico A"
          tecnicos={tecnicos}
          selected={id1}
          onChange={setId1}
          exclude={id2}
        />
        <SelectTecnico
          label="Técnico B"
          tecnicos={tecnicos}
          selected={id2}
          onChange={setId2}
          exclude={id1}
        />
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12 text-sm text-slate-400">
          <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Cargando comparación...
        </div>
      )}

      {!loading && s1 && s2 && (
        <div className="space-y-6">
          {/* Totales lado a lado */}
          <div className="grid grid-cols-2 gap-4">
            <TotalCard name={name1} total={s1.total} />
            <TotalCard name={name2} total={s2.total} />
          </div>

          {/* Categorias */}
          <div>
            <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Comparación por Categoría
            </h4>
            <div className="space-y-3">
              {allCats.sort().map((cat) => {
                const v1 = s1.porCategoria.find((c) => c.categoria === cat)?.total ?? 0;
                const v2 = s2.porCategoria.find((c) => c.categoria === cat)?.total ?? 0;
                const leader = v1 > v2 ? 1 : v2 > v1 ? 2 : 0;
                return (
                  <div key={cat}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-300">{cat}</span>
                      <span className="text-slate-500">
                        <span className={leader === 1 ? "text-amber-400 font-semibold" : ""}>{v1}</span>
                        {" vs "}
                        <span className={leader === 2 ? "text-amber-400 font-semibold" : ""}>{v2}</span>
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <div className="h-2.5 flex-1 overflow-hidden rounded-l-full bg-slate-700">
                        <div
                          className="h-full rounded-l-full bg-gradient-to-r from-amber-500 to-amber-400 transition-all"
                          style={{ width: `${(v1 / maxCat) * 100}%`, marginLeft: v1 === 0 ? 0 : undefined }}
                        />
                      </div>
                      <div className="h-2.5 flex-1 overflow-hidden rounded-r-full bg-slate-700">
                        <div
                          className="h-full rounded-r-full bg-gradient-to-l from-sky-500 to-sky-400 transition-all"
                          style={{ width: `${(v2 / maxCat) * 100}%`, marginLeft: "auto" }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Tendencia mensual lado a lado */}
          <div>
            <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Tendencia Mensual
            </h4>
            <div className="flex items-end gap-3" style={{ height: "140px" }}>
              {allMeses.map((key) => {
                const [anio, mes] = key.split("-").map(Number);
                const v1 = s1.porMes.find((m) => m.anio === anio && m.mes === mes)?.total ?? 0;
                const v2 = s2.porMes.find((m) => m.anio === anio && m.mes === mes)?.total ?? 0;
                return (
                  <div key={key} className="flex flex-1 flex-col items-center gap-0.5">
                    <span className="text-[10px] font-medium text-slate-400">{v1}</span>
                    <div
                      className="w-full rounded-t-sm bg-gradient-to-t from-amber-500 to-amber-400 transition-all"
                      style={{ height: `${(v1 / maxMes) * 55}px`, minHeight: v1 > 0 ? "2px" : "0px" }}
                      title={name1}
                    />
                    <div
                      className="w-full rounded-t-sm bg-gradient-to-t from-sky-500 to-sky-400 transition-all"
                      style={{ height: `${(v2 / maxMes) * 55}px`, minHeight: v2 > 0 ? "2px" : "0px" }}
                      title={name2}
                    />
                    <span className="mt-1 text-[10px] text-slate-500">{MONTHS[mes - 1]}</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-2 flex justify-center gap-6 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-sm bg-amber-500" /> {name1}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-sm bg-sky-500" /> {name2}
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function SelectTecnico({
  label, tecnicos, selected, onChange, exclude,
}: {
  label: string;
  tecnicos: Usuario[];
  selected: number | null;
  onChange: (id: number | null) => void;
  exclude: number | null;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">{label}</label>
      <select
        value={selected ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-amber-500/50 focus:outline-none"
      >
        {tecnicos
          .filter((t) => t.id !== exclude)
          .map((t) => (
            <option key={t.id} value={t.id}>{t.displayName}</option>
          ))}
      </select>
    </div>
  );
}

function TotalCard({ name, total }: { name: string; total: number }) {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-gradient-to-br from-slate-800 to-slate-900 p-4 text-center">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{name}</p>
      <p className="mt-1 text-3xl font-bold text-amber-400">{total}</p>
      <p className="text-xs text-slate-500">atenciones</p>
    </div>
  );
}
