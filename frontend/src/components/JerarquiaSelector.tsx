"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type {
  JerarquiaData,
  PadreJerarquia,
  GrupoJerarquia,
  AreaJerarquia,
  JerarquiaSelection,
} from "@/types";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api";

const PADRE_ICONS: Record<string, string> = {
  Académicos: "M12 14l9-5-9-5-9 5 9 5z M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z",
  Administrativos:
    "M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21",
  Extras:
    "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z",
};

interface Props {
  onChange: (sel: JerarquiaSelection) => void;
  value?: JerarquiaSelection;
}

export default function JerarquiaSelector({ onChange, value }: Props) {
  const [data, setData] = useState<JerarquiaData | null>(null);
  const [selPadre, setSelPadre] = useState<PadreJerarquia | null>(
    value?.padre ?? null
  );
  const [selGrupo, setSelGrupo] = useState<GrupoJerarquia | null>(
    value?.grupo ?? null
  );
  const [selArea, setSelArea] = useState<AreaJerarquia | null>(
    value?.area ?? null
  );
  const [areaFilter, setAreaFilter] = useState("");
  const [areaOpen, setAreaOpen] = useState(false);
  const areaRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!API) return;
    setLoading(true);
    const token = localStorage.getItem("auth_token") || "";
    fetch(`${API}/jerarquia/arbol`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((raw: { padres: any[]; grupos: any[]; areas: any[] }) => {
        const gruposByPadre: Record<number, any[]> = {};
        for (const g of raw.grupos) {
          if (!gruposByPadre[g.grupoPadreId]) gruposByPadre[g.grupoPadreId] = [];
          gruposByPadre[g.grupoPadreId].push({ ...g, areas: [] });
        }
        for (const a of raw.areas) {
          for (const padres of Object.values(gruposByPadre)) {
            for (const g of padres) {
              if (g.id === a.grupoId) {
                g.areas.push(a);
              }
            }
          }
        }
        const padres = raw.padres.map((p: any) => ({
          ...p,
          grupos: gruposByPadre[p.id] ?? [],
          areasDirectas: raw.areas.filter((a: any) => a.grupoPadreId === p.id && !a.grupoId),
        }));
        setData({ padres, areas: raw.areas, totalAreas: raw.areas.length });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (areaRef.current && !areaRef.current.contains(e.target as Node))
        setAreaOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const emit = useCallback(
    (p: PadreJerarquia | null, g: GrupoJerarquia | null, a: AreaJerarquia | null) => {
      onChange({ padre: p, grupo: g, area: a });
    },
    [onChange]
  );

  function pickPadre(p: PadreJerarquia) {
    setSelPadre(p);
    setSelGrupo(null);
    setSelArea(null);
    setAreaFilter("");
    emit(p, null, null);
  }

  function pickGrupo(g: GrupoJerarquia) {
    setSelGrupo(g);
    setSelArea(null);
    setAreaFilter("");
    emit(selPadre, g, null);
  }

  function pickArea(a: AreaJerarquia) {
    setSelArea(a);
    setAreaFilter(a.nombre);
    setAreaOpen(false);
    emit(selPadre, selGrupo, a);
  }

  function clearAll() {
    setSelPadre(null);
    setSelGrupo(null);
    setSelArea(null);
    setAreaFilter("");
    emit(null, null, null);
  }

  function clearPadre() {
    setSelPadre(null);
    setSelGrupo(null);
    setSelArea(null);
    setAreaFilter("");
    emit(null, null, null);
  }

  function clearGrupo() {
    setSelGrupo(null);
    setSelArea(null);
    setAreaFilter("");
    emit(selPadre, null, null);
  }

  function clearArea() {
    setSelArea(null);
    setAreaFilter("");
    emit(selPadre, selGrupo, null);
  }

  const filteredAreas: AreaJerarquia[] = (() => {
    if (selGrupo) return selGrupo.areas;
    if (selPadre && selPadre.grupos.length === 0)
      return selPadre.areasDirectas;
    return [];
  })();

  const displayedAreas = filteredAreas.filter(
    (a) =>
      !areaFilter ||
      a.nombre.toLowerCase().includes(areaFilter.toLowerCase())
  );

  const step = (selPadre ? 1 : 0) + (selGrupo ? 1 : 0) + (selArea ? 1 : 0);
  const needGrupo = selPadre && selPadre.grupos.length > 0;

  if (loading) {
    return (
      <div className="rounded-xl border border-white/10 bg-[#f8fafc] p-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#00754A] border-t-transparent" />
          <span className="text-sm text-[#6b7280]">Cargando jerarquía...</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-white/10 bg-[#f8fafc] p-6 text-center text-sm text-[#6b7280]">
        No se pudo cargar la jerarquía.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stepper */}
      <div className="flex items-center gap-1.5">
        {[1, 2, 3].map((n, i) => (
          <div key={n} className="flex items-center gap-1.5">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold transition ${
                (n === 1 && selPadre) || (n === 2 && selGrupo) || (n === 3 && selArea)
                  ? "bg-[#1e3932] text-white"
                  : n - 1 < step
                    ? "bg-[#00754A] text-white"
                    : "border border-[#d1d5db] text-[#6b7280]"
              }`}
            >
              {n}
            </span>
            {i < 2 && (
              <span
                className={`h-0.5 w-4 rounded ${
                  i < step ? "bg-[#00754A]" : "bg-[#f1f5f9]"
                }`}
              />
            )}
          </div>
        ))}
        <span className="ml-auto text-[11px] text-[#9ca3af]">
          {step}/3 niveles
        </span>
      </div>

      {/* Nivel 1 — Padre */}
      <div>
        <label className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[#6b7280]">
          Nivel 1 — Grupo Padre
          <span>{data.padres.length} opciones</span>
        </label>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {data.padres.map((p) => (
            <button
              key={p.id}
              onClick={() => pickPadre(p)}
              className={`group relative rounded-xl border-[1.5px] p-3.5 text-left transition ${
                selPadre?.id === p.id
                  ? "border-[#00754A] bg-[#00754A]/10 shadow-lg shadow-[#00754A]/10"
                  : "border-white/10 hover:border-[#d1d5db] hover:-translate-y-0.5"
              }`}
            >
              {selPadre?.id === p.id && (
                <span className="absolute right-2 top-2 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-[#00754A] text-[10px] text-white">
                  ✓
                </span>
              )}
              <div
                className={`mb-2 flex h-8 w-8 items-center justify-center rounded-lg ${
                  selPadre?.id === p.id
                    ? "bg-[#00754A] text-white"
                    : "bg-[#f1f5f9] text-[#4b5563]"
                }`}
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d={PADRE_ICONS[p.nombre] ?? PADRE_ICONS.Extras}
                  />
                </svg>
              </div>
              <h3 className="text-[13px] font-bold text-[#1e3932]">
                {p.nombre}
              </h3>
              <small className="text-[11px] text-[#6b7280]">
                {p.grupos.length ? `${p.grupos.length} grupos · ` : ""}{p.totalAreas} áreas
              </small>
              <span
                className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                  selPadre?.id === p.id
                    ? "bg-[#00754A] text-white"
                    : "bg-[#00754A]/10 text-[#00754A]"
                }`}
              >
                {p.totalAreas} áreas
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Nivel 2 — Grupo */}
      {selPadre && (
        <div>
          <label className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[#6b7280]">
            Nivel 2 — Grupo
            <span>
              {selPadre.grupos.length
                ? `${selPadre.grupos.length} grupos filtrados por ${selPadre.nombre}`
                : "0 grupos · directo a Área"}
            </span>
          </label>
          {selPadre.grupos.length === 0 ? (
            <p className="text-[12px] text-[#9ca3af]">
              Este GrupoPadre no tiene grupos intermedios — pasa directo a Área.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {selPadre.grupos.map((g) => (
                  <button
                    key={g.id}
                    onClick={() => pickGrupo(g)}
                    className={`rounded-full border-[1.5px] px-3.5 py-2 text-[13px] font-semibold transition ${
                      selGrupo?.id === g.id
                        ? "border-[#00754A] bg-[#00754A] text-white shadow-lg shadow-[#00754A]/25"
                        : "border-[#d1d5db] hover:border-white/30"
                    }`}
                  >
                    {g.nombre}{" "}
                    <span
                      className={`ml-1 rounded-full px-1.5 py-0.5 text-[11px] ${
                        selGrupo?.id === g.id
                          ? "bg-[#e5e7eb]"
                          : "bg-[#f3f4f6]"
                      }`}
                    >
                      {g.areas.length}
                    </span>
                  </button>
                ))}
              </div>
              <p className="mt-1.5 text-[11px] text-[#9ca3af]">
                Tip: {selPadre.grupos[0]?.nombre} concentra{" "}
                {selPadre.grupos[0]?.areas.length} áreas. Cambiar GrupoPadre
                resetea esta selección.
              </p>
            </>
          )}
        </div>
      )}

      {/* Nivel 3 — Área */}
      {selPadre && (
        <div>
          <label className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-[#6b7280]">
            Nivel 3 — Área
            <span>
              {filteredAreas.length
                ? `${filteredAreas.length} filtradas · ${data.totalAreas} totales`
                : "Selecciona Grupo primero"}
            </span>
          </label>
          <div ref={areaRef} className="relative">
            <div className="relative">
              <input
                type="text"
                value={areaFilter}
                onChange={(e) => {
                  setAreaFilter(e.target.value);
                  if (selArea && e.target.value !== selArea.nombre)
                    setSelArea(null);
                  setAreaOpen(true);
                  emit(selPadre, selGrupo, null);
                }}
                onFocus={() => filteredAreas.length && setAreaOpen(true)}
                disabled={!filteredAreas.length}
                placeholder={
                  filteredAreas.length
                    ? `Buscar área — ej. ${filteredAreas[0]?.nombre}…`
                    : "Selecciona Grupo primero…"
                }
                className="w-full rounded border-[1.5px] border-[#d1d5db] bg-[#f8fafc] px-3 py-2.5 text-[13px] font-medium text-[#1e3932] placeholder-slate-500 outline-none transition focus:border-[#00754A] focus:shadow-[0_0_0_3px_rgba(0,117,74,0.3)]"
              />
              <button
                onClick={() => filteredAreas.length && setAreaOpen(!areaOpen)}
                className="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded bg-[#1e3932] text-white"
              >
                ⌄
              </button>
            </div>
            {areaOpen && filteredAreas.length > 0 && (
              <div className="absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-xl border border-white/10 bg-[#f8fafc] shadow-2xl backdrop-blur-md">
                <div className="flex items-center justify-between border-b border-white/5 bg-[#f8fafc] px-3 py-2">
                  <span className="text-[11px] text-[#6b7280]">
                    <strong className="text-[#374151]">
                      {displayedAreas.length}
                    </strong>{" "}
                    resultados
                  </span>
                  <span className="text-[11px] text-[#9ca3af]">
                    {data.totalAreas} áreas totales
                  </span>
                </div>
                <div className="max-h-64 overflow-auto p-1.5">
                  {displayedAreas.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => pickArea(a)}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left transition ${
                        selArea?.id === a.id
                          ? "bg-[#00754A]/15 ring-1 ring-[#00754A]/30"
                          : "hover:bg-[#f8fafc]"
                      }`}
                    >
                      <div>
                        <div className="text-[13px] font-semibold text-[#1e3932]">
                          {a.nombre}
                        </div>
                        <div className="text-[11px] text-[#9ca3af]">
                          {a.grupo || "—"} · {a.grupoPadre}
                        </div>
                      </div>
                      <span
                        className={`text-[11px] ${
                          selArea?.id === a.id
                            ? "text-[#00754A]"
                            : "text-[#9ca3af]"
                        }`}
                      >
                        {selArea?.id === a.id ? "✓" : a.id}
                      </span>
                    </button>
                  ))}
                  {displayedAreas.length === 0 && (
                    <p className="py-4 text-center text-[13px] text-[#9ca3af]">
                      Sin resultados para &quot;{areaFilter}&quot;
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-[#f8fafc] p-2.5 ring-1 ring-white/5">
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#9ca3af]">
          Ruta
        </span>
        {selPadre ? (
          <>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#1e3932] px-2.5 py-1 text-[13px] font-semibold text-white">
              {selPadre.nombre}
              <button
                onClick={clearPadre}
                className="flex h-4 w-4 items-center justify-center rounded-full bg-[#e5e7eb] text-[10px] leading-none"
              >
                ×
              </button>
            </span>
            {selGrupo && (
              <>
                <span className="text-[#9ca3af]">›</span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#00754A] px-2.5 py-1 text-[13px] font-semibold text-white">
                  {selGrupo.nombre}
                  <button
                    onClick={clearGrupo}
                    className="flex h-4 w-4 items-center justify-center rounded-full bg-[#e5e7eb] text-[10px] leading-none"
                  >
                    ×
                  </button>
                </span>
              </>
            )}
            {selArea && (
              <>
                <span className="text-[#9ca3af]">›</span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-[#d1d5db] bg-[#f8fafc] px-2.5 py-1 text-[13px] font-semibold text-[#1e3932]">
                  {selArea.nombre}
                  <button
                    onClick={clearArea}
                    className="flex h-4 w-4 items-center justify-center rounded-full bg-[#f1f5f9] text-[10px] leading-none text-[#6b7280]"
                  >
                    ×
                  </button>
                </span>
              </>
            )}
            <button
              onClick={clearAll}
              className="ml-auto rounded-full border border-[#d1d5db] px-2.5 py-1 text-[11px] font-semibold text-[#6b7280] transition hover:border-white/30 hover:text-[#374151]"
            >
              Limpiar
            </button>
          </>
        ) : (
          <span className="text-[13px] text-[#9ca3af]">
            Selecciona GrupoPadre para comenzar…
          </span>
        )}
      </div>

      {/* Validación */}
      {selPadre && (
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] px-3 py-2 text-[12px] ring-1 ring-white/5">
          <span
            className={`h-2 w-2 rounded-full ${
              selArea && (!needGrupo || selGrupo)
                ? "bg-[#00754A]"
                : "bg-amber-500"
            }`}
          />
          <span className="text-[#6b7280]">
            {selArea && (!needGrupo || selGrupo)
              ? "Ruta válida"
              : `Completa ${
                  needGrupo && !selGrupo ? "Grupo y " : ""
                }Área para continuar`}
          </span>
        </div>
      )}
    </div>
  );
}
