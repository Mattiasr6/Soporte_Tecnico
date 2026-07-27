"use client";

import { useEffect, useState } from "react";
import { getAtenciones } from "@/lib/api";
import type { AtencionItem } from "@/types";

const CATEGORY_COLORS = [
  { dot: "bg-amber-500", bg: "bg-amber-500/10", text: "text-amber-300" },
  { dot: "bg-emerald-500", bg: "bg-emerald-500/10", text: "text-emerald-300" },
  { dot: "bg-sky-500", bg: "bg-sky-500/10", text: "text-sky-300" },
  { dot: "bg-violet-500", bg: "bg-violet-500/10", text: "text-violet-300" },
  { dot: "bg-rose-500", bg: "bg-rose-500/10", text: "text-rose-300" },
  { dot: "bg-orange-500", bg: "bg-orange-500/10", text: "text-orange-300" },
  { dot: "bg-cyan-500", bg: "bg-cyan-500/10", text: "text-cyan-300" },
  { dot: "bg-pink-500", bg: "bg-pink-500/10", text: "text-pink-300" },
];

const AREA_COLORS = [
  { bg: "bg-blue-500/10", text: "text-blue-300", border: "border-blue-500/20" },
  { bg: "bg-emerald-500/10", text: "text-emerald-300", border: "border-emerald-500/20" },
  { bg: "bg-violet-500/10", text: "text-violet-300", border: "border-violet-500/20" },
  { bg: "bg-rose-500/10", text: "text-rose-300", border: "border-rose-500/20" },
  { bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/20" },
  { bg: "bg-cyan-500/10", text: "text-cyan-300", border: "border-cyan-500/20" },
  { bg: "bg-orange-500/10", text: "text-orange-300", border: "border-orange-500/20" },
  { bg: "bg-pink-500/10", text: "text-pink-300", border: "border-pink-500/20" },
];

function hashColor(str: string, palette: any[]) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

export default function AtencionListModal({
  usuarioId,
  displayName,
  fechaDesde,
  fechaHasta,
  onClose,
}: {
  usuarioId: number;
  displayName: string;
  fechaDesde: string;
  fechaHasta: string;
  onClose: () => void;
}) {
  const [atenciones, setAtenciones] = useState<AtencionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => {
    setLoading(true);
    getAtenciones(usuarioId)
      .then((data) => setAtenciones(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [usuarioId]);

  const enRango = (fecha: string) => {
    const d = fecha.slice(0, 10);
    return d >= fechaDesde && d <= fechaHasta;
  };

  const filtradasPorFecha = atenciones.filter((a) => enRango(a.fechaRegistro));

  const q = busqueda.toLowerCase();
  const filtradas = q
    ? filtradasPorFecha.filter(
        (a) =>
          a.descripcion?.toLowerCase().includes(q) ||
          a.solucion?.toLowerCase().includes(q) ||
          a.areaSolicitante?.toLowerCase().includes(q) ||
          a.categoria?.toLowerCase().includes(q) ||
          a.colaboradorNombre?.toLowerCase().includes(q) ||
          a.medioSolicitud?.toLowerCase().includes(q),
      )
    : filtradasPorFecha;

  const fmtFecha = (iso: string) => {
    const [y, m, d] = iso.slice(0, 10).split("-");
    return `${d}/${m}/${y}`;
  };

  const fmtHora = (iso: string) => iso.slice(11, 16);

  // Summary metrics
  const categoriasUnicas = new Set(filtradasPorFecha.map((a) => a.categoria)).size;
  const areasUnicas = new Set(filtradasPorFecha.map((a) => a.areaSolicitante)).size;
  const fmtDesde = `${fechaDesde.slice(8, 10)}/${fechaDesde.slice(5, 7)}/${fechaDesde.slice(0, 4)}`;
  const fmtHasta = `${fechaHasta.slice(8, 10)}/${fechaHasta.slice(5, 7)}/${fechaHasta.slice(0, 4)}`;

  const initials = (displayName || "??")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-10 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="mx-4 flex w-full max-w-6xl flex-col rounded-2xl border border-slate-700/50 bg-slate-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ maxHeight: "85vh" }}
      >
        {/* ── Header ── */}
        <div className="flex shrink-0 items-center gap-4 border-b border-slate-700/50 bg-gradient-to-r from-slate-800/50 to-transparent px-6 py-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-500 to-amber-600 text-sm font-bold text-slate-950 shadow-lg shadow-amber-500/20">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-bold text-slate-100">{displayName}</h2>
            <p className="mt-0.5 truncate text-xs text-slate-500">
              {filtradasPorFecha.length} atencion{filtradasPorFecha.length !== 1 ? "es" : ""} &middot;{" "}
              {fmtDesde} &mdash; {fmtHasta}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar por descripción, área, categoría..."
                className="w-56 rounded-lg border border-slate-600 bg-slate-800 py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none"
              />
            </div>
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-white"
              title="Cerrar"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Summary bar ── */}
        <div className="grid shrink-0 grid-cols-4 gap-3 border-b border-slate-700/50 px-6 py-3">
          <div className="rounded-lg border border-slate-700/30 bg-gradient-to-br from-amber-500/10 to-transparent px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-amber-400/70">Total</p>
            <p className="mt-0.5 text-lg font-bold text-amber-300">{filtradasPorFecha.length}</p>
          </div>
          <div className="rounded-lg border border-slate-700/30 bg-gradient-to-br from-sky-500/10 to-transparent px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-sky-400/70">Categor&iacute;as</p>
            <p className="mt-0.5 text-lg font-bold text-sky-300">{categoriasUnicas}</p>
          </div>
          <div className="rounded-lg border border-slate-700/30 bg-gradient-to-br from-violet-500/10 to-transparent px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-violet-400/70">&Aacute;reas</p>
            <p className="mt-0.5 text-lg font-bold text-violet-300">{areasUnicas}</p>
          </div>
          <div className="rounded-lg border border-slate-700/30 bg-gradient-to-br from-emerald-500/10 to-transparent px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-400/70">Per&iacute;odo</p>
            <p className="mt-0.5 text-xs font-medium text-emerald-300">
              {fmtDesde} &mdash; {fmtHasta}
            </p>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="min-h-0 flex-1 overflow-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <svg className="h-6 w-6 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="mt-3 text-sm">Cargando atenciones...</span>
            </div>
          ) : filtradas.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <svg className="mb-3 h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                />
              </svg>
              <p className="text-sm">
                {busqueda ? "No se encontraron resultados." : "No hay atenciones en este per&iacute;odo."}
              </p>
            </div>
          ) : (
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="sticky top-0 border-b border-slate-700/50 bg-slate-900/95 backdrop-blur-sm">
                  <th className="w-[110px] whitespace-nowrap px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Fecha
                  </th>
                  <th className="w-[200px] whitespace-nowrap px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    &Aacute;rea
                  </th>
                  <th className="w-[120px] whitespace-nowrap px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Categor&iacute;a
                  </th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Descripci&oacute;n
                  </th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Soluci&oacute;n
                  </th>
                  <th className="w-[130px] whitespace-nowrap px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Colaborador
                  </th>
                  <th className="w-[100px] whitespace-nowrap px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Medio
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((a, i) => {
                  const catColor = hashColor(a.categoria || "", CATEGORY_COLORS);
                  const areaColor = hashColor(a.areaSolicitante || "", AREA_COLORS);
                  return (
                    <tr
                      key={a.id}
                      className={`border-b border-slate-800/50 text-slate-300 transition-colors hover:bg-slate-700/20 ${
                        i % 2 === 1 ? "bg-slate-800/10" : ""
                      }`}
                    >
                      {/* Fecha + hora */}
                      <td className="whitespace-nowrap px-4 py-3 align-top">
                        <div className="text-xs font-medium text-slate-200">{fmtFecha(a.fechaRegistro)}</div>
                        <div className="mt-0.5 text-[11px] text-slate-500">{fmtHora(a.fechaRegistro)}</div>
                      </td>

                      {/* Área — badge */}
                      <td className="whitespace-nowrap px-4 py-3 align-top">
                        <span
                          className={`inline-block rounded-md border ${areaColor.bg} ${areaColor.border} ${areaColor.text} px-2 py-0.5 text-[11px] font-medium`}
                        >
                          {a.areaSolicitante}
                        </span>
                      </td>

                      {/* Categoría — colored dot */}
                      <td className="whitespace-nowrap px-4 py-3 align-top">
                        <div className="flex items-center gap-1.5">
                          <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${catColor.dot}`} />
                          <span className="truncate text-xs text-slate-300">{a.categoria}</span>
                        </div>
                      </td>

                      {/* Descripción */}
                      <td className="px-4 py-3 align-top">
                        <p className="line-clamp-2 text-xs leading-relaxed text-slate-300" title={a.descripcion}>
                          {a.descripcion}
                        </p>
                      </td>

                      {/* Solución */}
                      <td className="px-4 py-3 align-top">
                        {a.solucion ? (
                          <p className="line-clamp-2 text-xs leading-relaxed text-slate-400" title={a.solucion}>
                            {a.solucion}
                          </p>
                        ) : (
                          <span className="text-xs italic text-slate-600">&mdash;</span>
                        )}
                      </td>

                      {/* Colaborador */}
                      <td className="whitespace-nowrap px-4 py-3 align-top text-xs text-slate-400">
                        {a.colaboradorNombre || <span className="italic text-slate-600">&mdash;</span>}
                      </td>

                      {/* Medio */}
                      <td className="whitespace-nowrap px-4 py-3 align-top">
                        <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-0.5 text-[11px] font-medium text-slate-400">
                          <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                            />
                          </svg>
                          {a.medioSolicitud || <span className="text-slate-600">&mdash;</span>}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="flex shrink-0 items-center justify-between border-t border-slate-700/50 px-6 py-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-flex items-center justify-center rounded-md bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400">
              {filtradas.length}
            </span>
            <span>
              de {filtradasPorFecha.length} atencion{filtradasPorFecha.length !== 1 ? "es" : ""}
              {busqueda && " (filtradas)"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className="h-1 w-1 rounded-full bg-slate-600" />
            <span>{displayName}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
