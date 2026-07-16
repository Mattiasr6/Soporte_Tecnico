"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import ToggleButton from "@/components/ToggleButton";
import AtencionTable from "@/components/AtencionTable";
import HistorialModal from "@/components/HistorialModal";
import { useAuth } from "@/components/AuthProvider";

export default function SoportePage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const [showHistorial, setShowHistorial] = useState(false);
  const [historialUserId, setHistorialUserId] = useState<number | undefined>(undefined);

  const tecnicoId = searchParams.get("tecnicoId");

  useEffect(() => {
    if (tecnicoId) {
      setHistorialUserId(Number(tecnicoId));
      setShowHistorial(true);
    }
  }, [tecnicoId]);

  return (
    <main className="mx-auto max-w-6xl space-y-4 px-3 py-4 lg:px-6 lg:py-6">
      <section className="flex flex-col items-center py-2">
        <h1 className="text-xl font-bold text-slate-100 lg:text-2xl">Panel del Técnico</h1>
        <p className="mt-0.5 text-xs text-slate-400 lg:text-sm">
          Cambia tu estado y registra las atenciones realizadas
        </p>
        <div className="mt-3">
          <ToggleButton />
        </div>
      </section>

      {/* Historial */}
      <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-4 py-3 lg:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Historial de Atenciones</h2>
            <p className="text-xs text-slate-500">
              {user?.role === "Jefe" || user?.canViewDashboard ? "Revisa las atenciones de todo el equipo" : "Revisa tus atenciones registradas"}
            </p>
          </div>
          <button
            onClick={() => { setHistorialUserId(undefined); setShowHistorial(true); }}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm font-medium text-slate-200 transition hover:border-amber-500 hover:text-amber-400 sm:w-auto sm:py-1.5"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Ver Histórico
          </button>
        </div>
      </section>

      <section>
        <h2 className="text-base font-semibold text-slate-100 lg:text-lg">
          Registro de Atenciones
        </h2>
        <p className="mt-0.5 text-xs text-slate-400 lg:text-sm">
          Ingresa todas las atenciones que realizaste
        </p>
        <div className="mt-3">
          <AtencionTable />
        </div>
      </section>

      {showHistorial && (
        <HistorialModal
          onClose={() => { setShowHistorial(false); setHistorialUserId(undefined); }}
          initialUsuarioId={historialUserId}
        />
      )}
    </main>
  );
}
