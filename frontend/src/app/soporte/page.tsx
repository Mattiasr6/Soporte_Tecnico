"use client";

import { useRef, useState } from "react";
import ToggleButton from "@/components/ToggleButton";
import AtencionTable from "@/components/AtencionTable";
import HistorialModal from "@/components/HistorialModal";
import { useAuth } from "@/components/AuthProvider";
import { importCsv } from "@/lib/api";

export default function SoportePage() {
  const { user } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [showHistorial, setShowHistorial] = useState(false);

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setResult(null);
    try {
      const res = await importCsv(file);
      setResult({
        ok: true,
        msg: `Se importaron ${res.registrosInsertados} registros.` +
          (res.errores ? `\n${res.errores.length} líneas con errores.` : ""),
      });
    } catch (err) {
      setResult({ ok: false, msg: err instanceof Error ? err.message : "Error al importar" });
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <main className="mx-auto max-w-6xl space-y-10 p-6">
      <section className="flex flex-col items-center pt-4">
        <h1 className="text-2xl font-bold text-slate-100">Panel del Técnico</h1>
        <p className="mt-1 text-sm text-slate-400">
          Cambia tu estado y registra las atenciones realizadas
        </p>
        <div className="mt-6">
          <ToggleButton />
        </div>
      </section>

      {/* CSV Import */}
      <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Importar desde CSV</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Sube tu archivo .csv para cargar atenciones al sistema
            </p>
          </div>
          <div className="flex items-center gap-3">
            {result && (
              <span className={`text-xs ${result.ok ? "text-emerald-400" : "text-red-400"}`}>
                {result.msg}
              </span>
            )}
            <button
              onClick={() => fileRef.current?.click()}
              disabled={importing}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-amber-500 hover:text-amber-400 disabled:opacity-50"
            >
              {importing ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Importando...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                  </svg>
                  Importar CSV
                </>
              )}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleImport}
              className="hidden"
            />
          </div>
        </div>
      </section>

      {/* Historial */}
      <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Historial de Atenciones</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {user?.role === "Jefe" ? "Revisa las atenciones de todo el equipo" : "Revisa tus atenciones registradas"}
            </p>
          </div>
          <button
            onClick={() => setShowHistorial(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-amber-500 hover:text-amber-400"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Ver Histórico
          </button>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-100">
          Registro de Atenciones
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Ingresa todas las atenciones que realizaste. Usa los botones{" "}
          <strong className="text-slate-300">+</strong> para observaciones y{" "}
          <strong className="text-sky-400">🔗</strong> para enlace de apoyo.
        </p>
        <div className="mt-4">
          <AtencionTable />
        </div>
      </section>

      {showHistorial && <HistorialModal onClose={() => setShowHistorial(false)} />}
    </main>
  );
}
