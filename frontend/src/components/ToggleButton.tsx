"use client";

import { useState } from "react";
import { updateEstado } from "@/lib/api";

export default function ToggleButton() {
  const [ocupado, setOcupado] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      const nuevo = !ocupado;
      await updateEstado(nuevo);
      setOcupado(nuevo);
    } catch (err) {
      console.error("Error al cambiar estado", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 select-none">
      <button
        onClick={handleToggle}
        disabled={loading}
        className="relative w-40 h-40 rounded-full focus:outline-none focus-visible:ring-4 focus-visible:ring-amber-400/60"
      >
        {/* anillo exterior pulsante */}
        <span
          className={`absolute inset-0 rounded-full transition-all duration-700 ${
            ocupado
              ? "animate-pulse shadow-[0_0_32px_8px_rgba(239,68,68,0.35)]"
              : "shadow-[0_0_32px_8px_rgba(34,197,94,0.35)]"
          }`}
        />

        {/* botón principal */}
        <span
          className={`absolute inset-1 rounded-full flex items-center justify-center text-white font-bold text-lg tracking-wider uppercase transition-all duration-300 active:scale-90 ${
            ocupado
              ? "bg-gradient-to-br from-red-500 to-red-700"
              : "bg-gradient-to-br from-emerald-400 to-emerald-600"
          }`}
        >
          {loading ? (
            <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <span className="drop-shadow-md">{ocupado ? "Ocupado" : "Disponible"}</span>
          )}
        </span>
      </button>

      <span
        className={`flex items-center gap-2 text-sm font-medium ${
          ocupado ? "text-red-400" : "text-emerald-400"
        }`}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            ocupado ? "bg-red-400" : "bg-emerald-400"
          }`}
        />
        {ocupado
          ? "Estás marcado como ocupado"
          : "Estás marcado como disponible"}
      </span>
    </div>
  );
}
