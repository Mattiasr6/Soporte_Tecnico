"use client";

import { Fragment, useState, useEffect } from "react";
import { AtencionRow } from "@/types";
import { createAtenciones, getAreas } from "@/lib/api";
import AreaAutocomplete from "./AreaAutocomplete";

const MEDIOS = ["Interno", "Presencial", "WhatsApp", "E-ticket"];
const USUARIOS_SOL = ["ADM", "BEC", "DOC"];
const CATEGORIAS = [
  "Audio/Video",
  "Cuentas/Accesos",
  "Hardware",
  "Impresión",
  "Otros",
  "Redes/Conectividad",
  "Sistemas académicos",
  "Software",
];

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

  useEffect(() => {
    getAreas()
      .then(setAreas)
      .catch(() => {});
  }, []);

  function patch(id: string, field: Partial<AtencionRow>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...field } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, blankRow()]);
  }

  function removeRow(id: string) {
    setRows((prev) => prev.filter((r) => r.id !== id));
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
          enlaceApoyo: r.enlaceApoyo || undefined,
          observaciones:
            r.requiereObservaciones && r.observaciones
              ? r.observaciones
              : undefined,
          fechaRegistro: new Date().toISOString().slice(0, 10),
        }))
      );
      setRows([blankRow()]);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  const validCount = rows.filter(
    (r) => r.areaSolicitante && r.descripcion.trim() && r.solucion.trim()
  ).length;

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/60 shadow-lg backdrop-blur-sm">
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
                  <td className="p-1.5">
                    <AreaAutocomplete
                      value={row.areaSolicitante}
                      onChange={(v) => patch(row.id, { areaSolicitante: v })}
                      areas={areas}
                      placeholder="Buscar área..."
                    />
                  </td>
                  <td className="p-1.5">
                    <select
                      value={row.medioSolicitud}
                      onChange={(e) => patch(row.id, { medioSolicitud: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                    >
                      {MEDIOS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-1.5">
                    <select
                      value={row.usuarioSolicitante}
                      onChange={(e) => patch(row.id, { usuarioSolicitante: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                    >
                      {USUARIOS_SOL.map((u) => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-1.5">
                    <select
                      value={row.categoria}
                      onChange={(e) => patch(row.id, { categoria: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                    >
                      <option value="">Seleccionar...</option>
                      {CATEGORIAS.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={row.descripcion}
                      onChange={(e) => patch(row.id, { descripcion: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                      placeholder="Ej: PC no enciende"
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={row.solucion}
                      onChange={(e) => patch(row.id, { solucion: e.target.value })}
                      className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                      placeholder="Ej: Se reemplazó fuente"
                    />
                  </td>
                  <td className="whitespace-nowrap p-1.5 text-center">
                    <label className="inline-flex items-center justify-center">
                      <input
                        type="checkbox"
                        checked={row.requiereObservaciones}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          patch(row.id, {
                            requiereObservaciones: checked,
                            showObservaciones: checked || row.showObservaciones,
                          });
                        }}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-amber-500 focus:ring-amber-500/50 focus:ring-offset-0"
                      />
                    </label>
                  </td>
                  <td className="p-1.5">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        type="button"
                        onClick={() => patch(row.id, { showObservaciones: !row.showObservaciones })}
                        className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${
                          row.showObservaciones || row.requiereObservaciones
                            ? "bg-amber-600 text-white"
                            : "bg-slate-700 text-slate-300 hover:bg-amber-600 hover:text-white"
                        }`}
                        title="Observaciones"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={() => patch(row.id, { showEnlaceApoyo: !row.showEnlaceApoyo })}
                        className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${
                          row.enlaceApoyo
                            ? "bg-sky-600 text-white"
                            : "bg-slate-700 text-slate-300 hover:bg-sky-600 hover:text-white"
                        }`}
                        title={row.enlaceApoyo ? "Enlace: " + row.enlaceApoyo : "Agregar enlace de apoyo"}
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                      </button>
                      {rows.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeRow(row.id)}
                          className="flex h-8 w-8 items-center justify-center rounded-lg text-lg text-slate-500 transition hover:bg-red-600 hover:text-white"
                          title="Eliminar fila"
                        >
                          &times;
                        </button>
                      )}
                    </div>
                  </td>
                </tr>

                {(row.showObservaciones || row.requiereObservaciones || row.showEnlaceApoyo) && (
                  <tr className="bg-slate-800/40">
                    <td colSpan={8} className="p-3">
                      <div className="space-y-3">
                        {(row.showObservaciones || row.requiereObservaciones) && (
                          <div className="flex items-start gap-3">
                            <textarea
                              value={row.observaciones}
                              onChange={(e) => patch(row.id, { observaciones: e.target.value })}
                              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                              rows={2}
                              placeholder="Describe aquí observaciones adicionales o detalles de la solución..."
                            />
                          </div>
                        )}
                        {row.showEnlaceApoyo && (
                          <div className="flex items-start gap-3">
                            <input
                              type="text"
                              value={row.enlaceApoyo}
                              onChange={(e) => patch(row.id, { enlaceApoyo: e.target.value })}
                              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/50"
                              placeholder="URL o referencia del enlace de apoyo"
                            />
                            {row.enlaceApoyo && (
                              <button
                                type="button"
                                onClick={() => patch(row.id, { showEnlaceApoyo: false })}
                                className="mt-1 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-700 hover:text-white"
                              >
                                Cerrar
                              </button>
                            )}
                          </div>
                        )}
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
        <button
          type="button"
          onClick={addRow}
          className="inline-flex items-center gap-2 rounded-lg border border-dashed border-slate-600 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-amber-500 hover:text-amber-400"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Agregar fila
        </button>

        <button
          type="button"
          onClick={handleSave}
          disabled={saving || validCount === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-6 py-2.5 text-sm font-bold text-slate-900 shadow-lg transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Guardando...
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Guardar atenciones ({validCount})
            </>
          )}
        </button>
      </div>
    </div>
  );
}
