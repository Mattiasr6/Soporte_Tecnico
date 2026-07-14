"use client";

import { useState, useEffect } from "react";
import { updateEstado, getUsuarios } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import type { Usuario } from "@/types";

export default function ToggleButton() {
  const { user, setUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showColabPicker, setShowColabPicker] = useState(false);
  const [colegas, setColegas] = useState<Usuario[]>([]);

  const estado = user?.estadoActual ?? "ausente";

  useEffect(() => {
    if (showColabPicker) {
      getUsuarios().then((lista) => {
        setColegas(lista.filter((c) => c.id !== user?.id));
      }).catch(() => {});
    }
  }, [showColabPicker, user?.id]);

  const handleToggle = () => {
    if (estado === "ausente") return;
    if (estado === "disponible") {
      setShowModal(true);
    } else {
      // Ocupado → Disponible: directo, sin modal
      setLoading(true);
      updateEstado("disponible").then(() => {
        if (user && setUser) setUser({ ...user, estadoActual: "disponible" });
      }).catch(console.error).finally(() => setLoading(false));
    }
  };

  const handleAtender = async () => {
    setShowModal(false);
    setLoading(true);
    try {
      await updateEstado("ocupado", "atendiendo");
      if (user && setUser) setUser({ ...user, estadoActual: "ocupado" });
    } catch (err) {
      console.error("Error al cambiar estado", err);
    } finally {
      setLoading(false);
    }
  };

  const handleColaborar = async (colaboradorId: number) => {
    setShowModal(false);
    setShowColabPicker(false);
    setLoading(true);
    try {
      await updateEstado("ocupado", "colaborando", colaboradorId);
      if (user && setUser) setUser({ ...user, estadoActual: "ocupado" });
    } catch (err) {
      console.error("Error al cambiar estado", err);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = estado === "ausente" || loading;

  return (
    <>
      <div className="flex flex-col items-center gap-4 select-none">
        <button
          onClick={handleToggle}
          disabled={isDisabled}
          className={`relative w-40 h-40 rounded-full focus:outline-none focus-visible:ring-4 focus-visible:ring-amber-400/60 ${
            estado === "ausente" ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
          }`}
        >
          {/* anillo exterior */}
          <span
            className={`absolute inset-0 rounded-full transition-all duration-700 ${
              estado === "ocupado"
                ? "animate-pulse shadow-[0_0_32px_8px_rgba(239,68,68,0.35)]"
                : estado === "disponible"
                  ? "shadow-[0_0_32px_8px_rgba(34,197,94,0.35)]"
                  : "shadow-[0_0_32px_8px_rgba(100,116,139,0.2)]"
            }`}
          />

          {/* botón principal */}
          <span
            className={`absolute inset-1 rounded-full flex items-center justify-center text-white font-bold text-lg tracking-wider uppercase transition-all duration-300 active:scale-90 ${
              estado === "ocupado"
                ? "bg-gradient-to-br from-red-500 to-red-700"
                : estado === "disponible"
                  ? "bg-gradient-to-br from-emerald-400 to-emerald-600"
                  : "bg-gradient-to-br from-slate-500 to-slate-700"
            }`}
          >
            {loading ? (
              <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <span className="drop-shadow-md">
                {estado === "ocupado" ? "Ocupado" : estado === "disponible" ? "Disponible" : "Ausente"}
              </span>
            )}
          </span>
        </button>

        <span
          className={`flex items-center gap-2 text-sm font-medium ${
            estado === "ocupado" ? "text-red-400" : estado === "disponible" ? "text-emerald-400" : "text-slate-400"
          }`}
        >
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              estado === "ocupado" ? "bg-red-400" : estado === "disponible" ? "bg-emerald-400" : "bg-slate-400"
            }`}
          />
          {estado === "ocupado"
            ? "Estás atendiendo"
            : estado === "disponible"
              ? "Estás disponible"
              : "No tienes conexión activa"}
        </span>
      </div>

      {/* Modal de selección */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setShowModal(false)}
        >
          <div
            className="mx-4 w-full max-w-md rounded-xl border border-slate-700/50 bg-slate-800/90 p-6 shadow-2xl backdrop-blur-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold text-slate-100">¿Qué vas a hacer?</h2>
            <p className="mt-1 text-sm text-slate-400">Selecciona tu motivo de ocupado</p>

            <div className="mt-5 space-y-3">
              {/* Opción Atender Caso */}
              <button
                onClick={handleAtender}
                className="flex w-full items-center gap-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-left transition-all hover:border-amber-500/50 hover:bg-amber-500/10"
              >
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xl">
                  🎧
                </span>
                <div>
                  <p className="font-semibold text-slate-100">Atender Caso</p>
                  <p className="text-sm text-slate-400">Te asignarán un ticket de soporte</p>
                </div>
              </button>

              {/* Opción Colaborar */}
              {!showColabPicker ? (
                <button
                  onClick={() => setShowColabPicker(true)}
                  className="flex w-full items-center gap-4 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 text-left transition-all hover:border-blue-500/50 hover:bg-blue-500/10"
                >
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xl">
                    👥
                  </span>
                  <div>
                    <p className="font-semibold text-slate-100">Colaborar con Colega</p>
                    <p className="text-sm text-slate-400">Ayudarás a otro técnico con su caso</p>
                  </div>
                </button>
              ) : (
                <div className="rounded-xl border border-slate-600/50 bg-slate-700/30 p-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
                    ¿Con quién vas a colaborar?
                  </p>
                  <div className="max-h-40 space-y-1 overflow-y-auto">
                    {colegas.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => handleColaborar(c.id)}
                        className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-slate-200 transition-all hover:bg-slate-600/50"
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400">
                          {c.displayName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
                        </span>
                        <div>
                          <p className="font-medium">{c.displayName}</p>
                          {c.especialidad && (
                            <p className="text-xs text-slate-500">{c.especialidad}</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => { setShowModal(false); setShowColabPicker(false); }}
              className="mt-4 w-full text-center text-sm text-slate-400 transition-colors hover:text-slate-200"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </>
  );
}
