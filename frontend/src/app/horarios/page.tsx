"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getUsuarios } from "@/lib/api";
import { useToast } from "@/components/Toast";
import type { Usuario } from "@/types";

const PLANTILLAS = [
  { label: "08:00 - 16:00", h1: "08:00", f1: "16:00", h2: "", f2: "" },
  { label: "08:00-12:00 + 14:30-18:30", h1: "08:00", f1: "12:00", h2: "14:30", f2: "18:30" },
  { label: "12:00 - 20:00", h1: "12:00", f1: "20:00", h2: "", f2: "" },
  { label: "07:00 - 15:00", h1: "07:00", f1: "15:00", h2: "", f2: "" },
  { label: "09:00 - 17:00", h1: "09:00", f1: "17:00", h2: "", f2: "" },
];

const MONTHS = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

interface CoberturaItem { franja: string; hora: string; tecnicos: string[]; }

function api(path: string, token: string, opts?: RequestInit) {
  const hostname = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return fetch(`http://${hostname}:5000/api${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts?.headers },
  });
}

interface HorarioForm {
  label: string;
  horaInicio1: string;
  horaFin1: string;
  horaInicio2: string;
  horaFin2: string;
}

export default function HorariosPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [tecnicos, setTecnicos] = useState<Usuario[]>([]);
  const [cobertura, setCobertura] = useState<CoberturaItem[]>([]);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [anio] = useState(new Date().getFullYear());
  const [forms, setForms] = useState<Record<number, HorarioForm>>({});
  const [loading, setLoading] = useState(true);
  const [editando, setEditando] = useState<number | null>(null);
  const [guardando, setGuardando] = useState(false);
  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) router.replace("/soporte");
  }, [user, canAccess, router]);

  const cargar = async () => {
    if (!token || !canAccess) return;
    const [u, c] = await Promise.all([
      getUsuarios(),
      api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json()),
    ]);
    setTecnicos(u);
    setCobertura((c as any).cobertura ?? []);

    const h = await api(`/horarios?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
    const map: Record<number, HorarioForm> = {};
    for (const hor of h as any[]) {
      map[hor.usuarioId] = {
        label: hor.label,
        horaInicio1: hor.horaInicio1 ?? "",
        horaFin1: hor.horaFin1 ?? "",
        horaInicio2: hor.horaInicio2 ?? "",
        horaFin2: hor.horaFin2 ?? "",
      };
    }
    setForms(map);
    setLoading(false);
  };

  useEffect(() => {
    if (token && canAccess) cargar();
  }, [token, mes, anio, canAccess]);

  const guardar = async (usuarioId: number) => {
    if (!token) return;
    const f = forms[usuarioId];
    // autogenerar label desde los bloques si no hay comentario
    const label = f?.label?.trim() || [
      f?.horaInicio1 && f?.horaFin1 ? `${f.horaInicio1}-${f.horaFin1}` : "",
      f?.horaInicio2 && f?.horaFin2 ? `${f.horaInicio2}-${f.horaFin2}` : "",
    ].filter(Boolean).join(" + ") || "Sin horario";
    try {
      await api("/horarios", token, {
        method: "POST",
        body: JSON.stringify({ ...f, label, usuarioId, mes, anio }),
      });
      toast("Horario guardado", "success");
      setEditando(null);
      const c = await api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
      setCobertura((c as any).cobertura ?? []);
    } catch { toast("Error al guardar", "error"); }
  };

  const guardarTodo = async () => {
    if (!token) return;
    setGuardando(true);
    let ok = 0, err = 0;
    for (const t of tecnicos) {
      const f = forms[t.id];
      if (!f) continue;
      const label = f.label?.trim() || [
        f.horaInicio1 && f.horaFin1 ? `${f.horaInicio1}-${f.horaFin1}` : "",
        f.horaInicio2 && f.horaFin2 ? `${f.horaInicio2}-${f.horaFin2}` : "",
      ].filter(Boolean).join(" + ") || "Sin horario";
      try {
        await api("/horarios", token, {
          method: "POST",
          body: JSON.stringify({ ...f, label, usuarioId: t.id, mes, anio }),
        });
        ok++;
      } catch { err++; }
    }
    setGuardando(false);
    setEditando(null);
    if (err === 0) toast(`Todos los horarios guardados (${ok})`, "success");
    else toast(`${ok} guardados, ${err} errores`, "error");
    const c = await api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
    setCobertura((c as any).cobertura ?? []);
  };

  const aplicarPlantilla = (usuarioId: number, p: typeof PLANTILLAS[number]) => {
    setForms((prev) => ({
      ...prev,
      [usuarioId]: { label: p.label, horaInicio1: p.h1, horaFin1: p.f1, horaInicio2: p.h2, horaFin2: p.f2 },
    }));
  };

  const limpiar = async (usuarioId: number) => {
    if (!token) return;
    try {
      const h = await api(`/horarios?mes=${mes}&anio=${anio}`, token).then((r) => r.json()) as any[];
      const hor = h.find((x: any) => x.usuarioId === usuarioId);
      if (hor?.id) {
        await api(`/horarios/${hor.id}`, token, { method: "DELETE" });
        toast("Horario eliminado", "info");
      }
      setForms((prev) => { const n = { ...prev }; delete n[usuarioId]; return n; });
      const c = await api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
      setCobertura((c as any).cobertura ?? []);
    } catch {}
  };

  if (!user || !canAccess) return null;

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 lg:text-2xl">Gestión de Horarios</h1>
        <p className="mt-0.5 text-xs text-slate-400 lg:text-sm">
          Asigna los horarios del equipo para {MONTHS[mes - 1]} {anio}
        </p>
      </div>

      <select value={mes} onChange={(e) => setMes(Number(e.target.value))}
        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200">
        {MONTHS.map((m, i) => (<option key={i} value={i + 1}>{m}</option>))}
      </select>

      {loading ? (
        <div className="flex justify-center py-12 text-slate-500">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="ml-2 text-sm">Cargando...</span>
        </div>
      ) : (
        <>
          <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Horarios — {MONTHS[mes - 1]} {anio}
            </h2>

            <div className="mb-4 flex flex-wrap gap-2">
              {PLANTILLAS.map((p) => (
                <button key={p.label}
                  onClick={() => { if (editando !== null) aplicarPlantilla(editando, p); }}
                  disabled={editando === null}
                  className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300 transition hover:border-amber-500 hover:text-amber-400 disabled:opacity-40"
                >
                  {p.label}
                </button>
              ))}
              <span className="self-center text-[10px] text-slate-500">(selecciona un técnico y aplica)</span>
            </div>

            <div className="mb-4 flex items-center justify-between">
              <span className="text-[10px] text-slate-500">
                {tecnicos.filter((t) => forms[t.id]?.horaInicio1).length} de {tecnicos.length} técnicos con horario
              </span>
              <button onClick={guardarTodo} disabled={guardando}
                className="rounded-lg bg-emerald-500 px-4 py-1.5 text-xs font-bold text-slate-900 transition hover:bg-emerald-400 disabled:opacity-50">
                {guardando ? "Guardando..." : "Guardar todo"}
              </button>
            </div>

            <div className="space-y-2">
              {tecnicos.map((t) => {
                const f = forms[t.id];
                const activo = editando === t.id;
                return (
                  <div key={t.id} className={`rounded-xl border p-3 transition ${activo ? "border-amber-500/40 bg-slate-800/60" : "border-slate-700/40 bg-slate-800/30"}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-200">{t.displayName}</span>
                      <div className="flex items-center gap-2">
                        {f?.label && !activo && <span className="text-xs text-slate-500">{f.label}</span>}
                        <button onClick={() => setEditando(activo ? null : t.id)}
                          className="rounded-lg px-3 py-1 text-xs text-slate-400 transition hover:bg-slate-700 hover:text-slate-200">
                          {activo ? "Cancelar" : f?.label ? "Editar" : "Asignar"}
                        </button>
                        {f?.label && (
                          <button onClick={() => limpiar(t.id)}
                            className="rounded-lg px-2 py-1 text-xs text-red-400/70 transition hover:bg-red-600/20 hover:text-red-400">✕</button>
                        )}
                      </div>
                    </div>
                    {activo && (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="w-16 text-xs text-slate-500">Bloque 1</span>
                          <input type="time" value={f?.horaInicio1 ?? ""}
                            onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaInicio1: e.target.value } }))}
                            className="rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100" />
                          <span className="text-xs text-slate-600">a</span>
                          <input type="time" value={f?.horaFin1 ?? ""}
                            onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaFin1: e.target.value } }))}
                            className="rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100" />
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-16 text-xs text-slate-500">Bloque 2</span>
                          <input type="time" value={f?.horaInicio2 ?? ""}
                            onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaInicio2: e.target.value } }))}
                            className="rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100" />
                          <span className="text-xs text-slate-600">a</span>
                          <input type="time" value={f?.horaFin2 ?? ""}
                            onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaFin2: e.target.value } }))}
                            className="rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100" />
                          <span className="text-[10px] text-slate-600">(opcional)</span>
                        </div>
                        <div className="flex gap-2">
                          <input type="text" value={f?.label ?? ""}
                            onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), label: e.target.value } }))}
                            placeholder="Comentario (opcional)"
                            className="flex-1 rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-100 placeholder-slate-600" />
                          <button onClick={() => guardar(t.id)}
                            className="rounded-lg bg-amber-500 px-4 py-1 text-xs font-bold text-slate-900 transition hover:bg-amber-400">Guardar</button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Cobertura — {MONTHS[mes - 1]} {anio}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {cobertura.map((c) => (
                <div key={c.franja} className="rounded-xl border border-slate-700/40 bg-slate-800/50 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-200">{c.franja}</h3>
                    <span className="text-[10px] font-medium uppercase tracking-wider text-amber-400">{c.hora}</span>
                  </div>
                  {c.tecnicos.length === 0 ? (
                    <p className="mt-2 text-xs text-slate-500">Sin cobertura</p>
                  ) : (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {c.tecnicos.map((nom) => (
                        <span key={nom} className="inline-flex items-center gap-1.5 rounded-full bg-slate-700/60 px-3 py-1 text-xs text-slate-200">
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          {nom}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

function emptyForm(): HorarioForm {
  return { label: "", horaInicio1: "", horaFin1: "", horaInicio2: "", horaFin2: "" };
}
