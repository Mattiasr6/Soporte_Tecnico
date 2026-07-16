"use client";

import { Fragment, useState, useEffect, useRef } from "react";
import { AtencionRow } from "@/types";
import { createAtenciones, getAreas, getAtenciones } from "@/lib/api";
import { useToast } from "./Toast";
import AreaAutocomplete from "./AreaAutocomplete";

const MEDIOS = ["Interno", "Presencial", "WhatsApp", "E-ticket"];
const USUARIOS_SOL = ["ADM", "BEC", "DOC"];
const CATEGORIAS = [
  "Audio/Video", "Cuentas/Accesos", "Hardware", "Impresión",
  "Otros", "Redes/Conectividad", "Sistemas académicos", "Software",
];

const PLANTILLAS = [
  { label: "Conectividad", categoria: "Redes/Conectividad", descripcion: "Sin acceso a internet en oficina", solucion: "Se reinicio switch y se reconfiguro VLAN", area: "Sistemas" },
  { label: "Impresora", categoria: "Impresión", descripcion: "Impresora no imprime", solucion: "Se limpio cabezal y se reemplazo toner", area: "Sistemas" },
  { label: "PC no enciende", categoria: "Hardware", descripcion: "CPU no enciende", solucion: "Se reemplazo fuente de poder", area: "Sistemas" },
  { label: "Correo", categoria: "Software", descripcion: "Outlook no sincroniza", solucion: "Se reconfiguro perfil de correo", area: "Sistemas" },
  { label: "Proyector", categoria: "Audio/Video", descripcion: "Proyector no da imagen", solucion: "Se reemplazo cable HDMI", area: "Laboratorios" },
];

interface Sugerencia {
  descripcion: string;
  solucion: string;
  categoria: string;
  area: string;
  medio: string;
}

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function blankRow(): AtencionRow {
  return {
    id: uid(),
    areaSolicitante: "",
    medioSolicitud: "Interno",
    usuarioSolicitante: "ADM",
    categoria: "",
    descripcion: "",
    solucion: "",
    colaboradorId: null,
    showObservaciones: false,
    requiereObservaciones: false,
    observaciones: "",
    showEnlaceApoyo: false,
    enlaceApoyo: "",
  };
}

export default function AtencionTable() {
  const [rows, setRows] = useState<AtencionRow[]>([blankRow()]);
  const [saving, setSaving] = useState(false);
  const [areas, setAreas] = useState<string[]>([]);
  const [tecnicos, setTecnicos] = useState<{ id: number; displayName: string }[]>([]);
  const [sugerencias, setSugerencias] = useState<Sugerencia[]>([]);
  const [mostrarSug, setMostrarSug] = useState<string | null>(null);
  const [indiceBusqueda, setIndiceBusqueda] = useState<{ keywords: string; sug: Sugerencia }[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const sugRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    getAreas().then(setAreas).catch(() => {});
    import("@/lib/api").then((api) => api.getUsuarios()).then(setTecnicos).catch(() => {});
    getAtenciones().then((data) => {
      const index: { keywords: string; sug: Sugerencia }[] = [];
      const unique = new Map<string, Sugerencia>();
      for (const a of data) {
        const key = `${a.descripcion}|${a.solucion}`;
        if (!unique.has(key)) {
          unique.set(key, {
            descripcion: a.descripcion,
            solucion: a.solucion,
            categoria: a.categoria,
            area: a.areaSolicitante,
            medio: a.medioSolicitud,
          });
        }
      }
      for (const sug of unique.values()) {
        const words = (sug.descripcion + " " + sug.solucion + " " + sug.categoria).toLowerCase().split(/\s+/).filter(Boolean);
        for (const w of words) {
          if (w.length > 2) index.push({ keywords: w, sug });
        }
      }
      setIndiceBusqueda(index);
      setSugerencias([...unique.values()].slice(0, 50));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (sugRef.current && !sugRef.current.contains(e.target as Node)) setMostrarSug(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function patch(id: string, field: Partial<AtencionRow>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...field } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, blankRow()]);
    setActiveIndex(rows.length);
  }

  function removeRow(id: string) {
    setRows((prev) => {
      const idx = prev.findIndex((r) => r.id === id);
      const next = prev.filter((r) => r.id !== id);
      if (next.length === 0) next.push(blankRow());
      return next;
    });
    setActiveIndex((prev) => Math.min(prev, rows.length - 2));
  }

  function aplicarPlantilla(plantilla: typeof PLANTILLAS[number]) {
    setRows((prev) => {
      const first = prev[0];
      if (first && !first.areaSolicitante && !first.descripcion && !first.solucion) {
        return [{
          ...first,
          areaSolicitante: plantilla.area,
          categoria: plantilla.categoria,
          descripcion: plantilla.descripcion,
          solucion: plantilla.solucion,
          medioSolicitud: "Interno",
        }, ...prev.slice(1)];
      }
      const newRow = { ...blankRow(), areaSolicitante: plantilla.area, categoria: plantilla.categoria, descripcion: plantilla.descripcion, solucion: plantilla.solucion };
      return [newRow, ...prev];
    });
    toast(`Plantilla "${plantilla.label}" aplicada`, "info");
  }

  function buscarSugerencias(texto: string): Sugerencia[] {
    if (!texto || texto.length < 3) return [];
    const q = texto.toLowerCase();
    const words = q.split(/\s+/).filter((w) => w.length > 2);
    if (words.length === 0) return [];

    const scores = new Map<Sugerencia, number>();
    for (const w of words) {
      for (const entry of indiceBusqueda) {
        if (entry.keywords.startsWith(w) || entry.keywords.includes(w)) {
          scores.set(entry.sug, (scores.get(entry.sug) ?? 0) + 1);
        }
      }
    }
    return [...scores.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([sug]) => sug);
  }

  function onDescripcionChange(id: string, value: string) {
    patch(id, { descripcion: value });
    const sug = buscarSugerencias(value);
    if (sug.length > 0) {
      setMostrarSug(id);
      setSugerencias(sug);
    } else {
      setMostrarSug(null);
    }
  }

  function aplicarSugerencia(id: string, sug: Sugerencia) {
    patch(id, {
      descripcion: sug.descripcion,
      solucion: sug.solucion,
      categoria: sug.categoria,
      areaSolicitante: sug.area,
      medioSolicitud: sug.medio,
    });
    setMostrarSug(null);
    toast("Campos autocompletados", "success");
  }

  async function handleSave() {
    const valid = rows.filter(
      (r) => r.areaSolicitante && r.descripcion.trim() && r.solucion.trim()
    );
    if (!valid.length) return;

    setSaving(true);
    try {
      await createAtenciones(
        valid.map((r) => ({
          areaSolicitante: r.areaSolicitante,
          medioSolicitud: r.medioSolicitud,
          usuarioSolicitante: r.usuarioSolicitante,
          categoria: r.categoria,
          descripcion: r.descripcion,
          solucion: r.solucion,
          colaboradorId: r.colaboradorId ?? undefined,
          enlaceApoyo: r.enlaceApoyo || undefined,
          observaciones: r.requiereObservaciones && r.observaciones ? r.observaciones : undefined,
          fechaRegistro: new Date().toISOString().slice(0, 10),
        }))
      );
      toast(`${valid.length} atencion${valid.length !== 1 ? "es" : ""} guardada${valid.length !== 1 ? "s" : ""}`, "success");
      setRows([blankRow()]);
      setActiveIndex(0);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Error al guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  const validCount = rows.filter(
    (r) => r.areaSolicitante && r.descripcion.trim() && r.solucion.trim()
  ).length;

  const activeRow = rows[activeIndex];

  // ---- MOBILE CARD VIEW ----
  const MobileCard = ({ row }: { row: AtencionRow }) => (
    <div className="space-y-3 rounded-xl border border-slate-700/50 bg-slate-800/60 p-4">
      <AreaAutocomplete
        value={row.areaSolicitante}
        onChange={(v) => patch(row.id, { areaSolicitante: v })}
        areas={areas}
        placeholder="Área solicitante..."
      />

      <div className="grid grid-cols-2 gap-2">
        <select value={row.medioSolicitud} onChange={(e) => patch(row.id, { medioSolicitud: e.target.value })}
          className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100">
          {MEDIOS.map((m) => (<option key={m} value={m}>{m}</option>))}
        </select>
        <select value={row.usuarioSolicitante} onChange={(e) => patch(row.id, { usuarioSolicitante: e.target.value })}
          className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100">
          {USUARIOS_SOL.map((u) => (<option key={u} value={u}>{u}</option>))}
        </select>
      </div>

      <select value={row.categoria} onChange={(e) => patch(row.id, { categoria: e.target.value })}
        className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100">
        <option value="">Categoría...</option>
        {CATEGORIAS.map((c) => (<option key={c} value={c}>{c}</option>))}
      </select>

      <div className="relative">
        <input type="text" value={row.descripcion}
          onChange={(e) => onDescripcionChange(row.id, e.target.value)}
          onFocus={() => {
            const sug = buscarSugerencias(row.descripcion);
            if (sug.length > 0) { setMostrarSug(row.id); setSugerencias(sug); }
          }}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500"
          placeholder="Descripción del problema" autoComplete="off" />
        {mostrarSug === row.id && sugerencias.length > 0 && (
          <div ref={sugRef} className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded-lg border border-slate-700 bg-slate-900 shadow-2xl">
            {sugerencias.map((s, i) => (
              <button key={i} onClick={() => aplicarSugerencia(row.id, s)}
                className="w-full px-3 py-2 text-left text-xs text-slate-300 transition hover:bg-amber-600/20 hover:text-amber-400">
                <span className="font-medium">{s.descripcion}</span>
                <span className="ml-2 text-slate-500">→ {s.solucion}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <input type="text" value={row.solucion} onChange={(e) => patch(row.id, { solucion: e.target.value })}
        className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500"
        placeholder="Solución aplicada" />

      {/* Acciones en fila */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={row.requiereObservaciones}
            onChange={(e) => {
              const checked = e.target.checked;
              patch(row.id, { requiereObservaciones: checked, showObservaciones: checked || row.showObservaciones });
            }}
            className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-amber-500" />
          +1h
        </label>

        {/* Colaborador */}
        <select value={row.colaboradorId ?? ""} onChange={(e) => patch(row.id, { colaboradorId: e.target.value ? Number(e.target.value) : null })}
          className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100">
          <option value="">Ninguno</option>
          {tecnicos.map((t) => (
            <option key={t.id} value={t.id}>{t.displayName}</option>
          ))}
        </select>

        <button type="button" onClick={() => patch(row.id, { showObservaciones: !row.showObservaciones })}
          className={`flex h-8 items-center gap-1 rounded-lg px-2 text-xs transition ${row.showObservaciones || row.requiereObservaciones ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-amber-600 hover:text-white"}`}>
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          Obs
        </button>

        <button type="button" onClick={() => patch(row.id, { showEnlaceApoyo: !row.showEnlaceApoyo })}
          className={`flex h-8 items-center gap-1 rounded-lg px-2 text-xs transition ${row.enlaceApoyo ? "bg-sky-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-sky-600 hover:text-white"}`}>
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
          </svg>
          Link
        </button>

        {rows.length > 1 && (
          <button type="button" onClick={() => removeRow(row.id)}
            className="flex h-8 items-center rounded-lg bg-slate-700 px-2 text-xs text-slate-400 transition hover:bg-red-600 hover:text-white">
            Eliminar
          </button>
        )}
      </div>

      {/* Expandibles */}
      {(row.showObservaciones || row.requiereObservaciones) && (
        <textarea value={row.observaciones} onChange={(e) => patch(row.id, { observaciones: e.target.value })}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500"
          rows={2} placeholder="Observaciones..." />
      )}
      {row.showEnlaceApoyo && (
        <div className="flex gap-2">
          <input type="text" value={row.enlaceApoyo} onChange={(e) => patch(row.id, { enlaceApoyo: e.target.value })}
            className="flex-1 rounded-lg border border-sky-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500"
            placeholder="URL de apoyo" />
          {row.enlaceApoyo && (
            <button type="button" onClick={() => patch(row.id, { showEnlaceApoyo: false })}
              className="rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-700">Cerrar</button>
          )}
        </div>
      )}
    </div>
  );
  return (
    <div className="space-y-4">
      {/* Plantillas rapidas */}
      <div className="flex flex-wrap gap-2">
        {PLANTILLAS.map((p) => (
          <button key={p.label} onClick={() => aplicarPlantilla(p)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-amber-500/50 hover:bg-slate-800 hover:text-amber-400">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {p.label}
          </button>
        ))}
        <span className="self-center text-[10px] text-slate-600">Plantillas rápidas</span>
      </div>

      <div className="block md:hidden space-y-3">
        {/* Dots de navegación */}
        {rows.length > 1 && (
          <div className="flex items-center justify-center gap-2">
            {rows.map((_, i) => (
              <button key={i} onClick={() => setActiveIndex(i)}
                className={`h-2 rounded-full transition-all ${i === activeIndex ? "w-6 bg-amber-500" : "w-2 bg-slate-600"}`} />
            ))}
          </div>
        )}

        {rows.length > 1 && (
          <p className="text-center text-xs text-slate-500">Ticket {activeIndex + 1} de {rows.length}</p>
        )}

        {activeRow && MobileCard({ row: activeRow })}

        {rows.length > 1 && (
          <div className="flex justify-between gap-2">
            <button type="button" disabled={activeIndex === 0}
              onClick={() => setActiveIndex((p) => Math.max(0, p - 1))}
              className="rounded-lg bg-slate-700 px-4 py-2 text-xs text-slate-300 transition hover:bg-slate-600 disabled:opacity-30">
              ← Anterior
            </button>
            <button type="button" disabled={activeIndex >= rows.length - 1}
              onClick={() => setActiveIndex((p) => Math.min(rows.length - 1, p + 1))}
              className="rounded-lg bg-slate-700 px-4 py-2 text-xs text-slate-300 transition hover:bg-slate-600 disabled:opacity-30">
              Siguiente →
            </button>
          </div>
        )}
      </div>

      {/* Vista Desktop (tabla) */}
      <div className="hidden md:block overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/60 shadow-lg backdrop-blur-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800 text-slate-300">
                <th className="min-w-[200px] p-3 text-left font-semibold tracking-wide">Área solicitante</th>
                <th className="min-w-[120px] p-3 text-left font-semibold tracking-wide">Medio</th>
                <th className="min-w-[90px] p-3 text-left font-semibold tracking-wide">Usuario</th>
                <th className="min-w-[150px] p-3 text-left font-semibold tracking-wide">Categoría</th>
                <th className="min-w-[180px] p-3 text-left font-semibold tracking-wide">Descripción</th>
                <th className="min-w-[180px] p-3 text-left font-semibold tracking-wide">Solución</th>
                <th className="whitespace-nowrap p-3 text-center font-semibold tracking-wide">+1h</th>
                <th className="p-3 text-center font-semibold tracking-wide">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <Fragment key={row.id}>
                  <tr className="border-b border-slate-700/50 transition-colors hover:bg-slate-700/40">
                    <td className="p-1.5"><AreaAutocomplete value={row.areaSolicitante} onChange={(v) => patch(row.id, { areaSolicitante: v })} areas={areas} placeholder="Buscar área..." /></td>
                    <td className="p-1.5"><select value={row.medioSolicitud} onChange={(e) => patch(row.id, { medioSolicitud: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100">{MEDIOS.map((m) => (<option key={m} value={m}>{m}</option>))}</select></td>
                    <td className="p-1.5"><select value={row.usuarioSolicitante} onChange={(e) => patch(row.id, { usuarioSolicitante: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100">{USUARIOS_SOL.map((u) => (<option key={u} value={u}>{u}</option>))}</select></td>
                    <td className="p-1.5"><select value={row.categoria} onChange={(e) => patch(row.id, { categoria: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100"><option value="">Seleccionar...</option>{CATEGORIAS.map((c) => (<option key={c} value={c}>{c}</option>))}</select></td>
                    <td className="p-1.5 relative">
                      <input type="text" value={row.descripcion} onChange={(e) => onDescripcionChange(row.id, e.target.value)}
                        onFocus={() => { const sug = buscarSugerencias(row.descripcion); if (sug.length > 0) { setMostrarSug(row.id); setSugerencias(sug); } }}
                        className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500" placeholder="Ej: PC no enciende" autoComplete="off" />
                      {mostrarSug === row.id && sugerencias.length > 0 && (
                        <div ref={sugRef} className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-auto rounded-lg border border-slate-700 bg-slate-900 shadow-2xl">
                          {sugerencias.map((s, i) => (<button key={i} onClick={() => aplicarSugerencia(row.id, s)}
                            className="w-full px-3 py-2 text-left text-xs text-slate-300 transition hover:bg-amber-600/20 hover:text-amber-400">
                            <span className="font-medium">{s.descripcion}</span><span className="ml-2 text-slate-500">→ {s.solucion}</span><span className="ml-2 text-[10px] text-slate-600">({s.categoria})</span></button>))}
                        </div>
                      )}
                    </td>
                    <td className="p-1.5"><input type="text" value={row.solucion} onChange={(e) => patch(row.id, { solucion: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500" placeholder="Ej: Se reemplazó fuente" /></td>
                    <td className="whitespace-nowrap p-1.5 text-center"><label className="inline-flex items-center justify-center">
                      <input type="checkbox" checked={row.requiereObservaciones}
                        onChange={(e) => { const checked = e.target.checked; patch(row.id, { requiereObservaciones: checked, showObservaciones: checked || row.showObservaciones }); }}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-amber-500 focus:ring-amber-500/50" /></label></td>
                    <td className="p-1.5">
                      <div className="flex items-center justify-center gap-1">
                        <select value={row.colaboradorId ?? ""} onChange={(e) => patch(row.id, { colaboradorId: e.target.value ? Number(e.target.value) : null })}
                          className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-2 text-xs text-slate-100">
                          <option value="">Ninguno</option>
                          {tecnicos.map((t) => (
                            <option key={t.id} value={t.id}>{t.displayName}</option>
                          ))}
                        </select>
                        <button type="button" onClick={() => patch(row.id, { showObservaciones: !row.showObservaciones })}
                          className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${row.showObservaciones || row.requiereObservaciones ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-amber-600 hover:text-white"}`} title="Observaciones">
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></button>
                        <button type="button" onClick={() => patch(row.id, { showEnlaceApoyo: !row.showEnlaceApoyo })}
                          className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${row.enlaceApoyo ? "bg-sky-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-sky-600 hover:text-white"}`} title={row.enlaceApoyo ? "Enlace: " + row.enlaceApoyo : "Agregar enlace de apoyo"}>
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg></button>
                        {rows.length > 1 && (
                          <button type="button" onClick={() => removeRow(row.id)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-lg text-slate-500 transition hover:bg-red-600 hover:text-white" title="Eliminar fila">&times;</button>)}
                      </div>
                    </td>
                  </tr>
                  {(row.showObservaciones || row.requiereObservaciones || row.showEnlaceApoyo) && (
                    <tr className="bg-slate-800/40">
                      <td colSpan={8} className="p-3">
                        <div className="space-y-3">
                          {(row.showObservaciones || row.requiereObservaciones) && (
                            <textarea value={row.observaciones} onChange={(e) => patch(row.id, { observaciones: e.target.value })}
                              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500" rows={2} placeholder="Describe aquí observaciones adicionales o detalles de la solución..." />)}
                          {row.showEnlaceApoyo && (
                            <div className="flex items-start gap-3">
                              <input type="text" value={row.enlaceApoyo} onChange={(e) => patch(row.id, { enlaceApoyo: e.target.value })}
                                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500" placeholder="URL o referencia del enlace de apoyo" />
                              {row.enlaceApoyo && (<button type="button" onClick={() => patch(row.id, { showEnlaceApoyo: false })}
                                className="mt-1 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-700 hover:text-white">Cerrar</button>)}
                            </div>)}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <button type="button" onClick={addRow}
          className="inline-flex items-center gap-2 rounded-lg border border-dashed border-slate-600 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-amber-500 hover:text-amber-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
          Agregar fila
        </button>
        <button type="button" onClick={handleSave} disabled={saving || validCount === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-6 py-2.5 text-sm font-bold text-slate-900 shadow-lg transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40">
          {saving ? (
            <><svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Guardando...</>
          ) : (
            <><svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>Guardar atenciones ({validCount})</>
          )}
        </button>
      </div>
    </div>
  );
}
