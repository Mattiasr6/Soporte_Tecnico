"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
  return fetch(`http://${hostname}:5001/api${path}`, {
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

function emptyForm(): HorarioForm {
  return { label: "", horaInicio1: "", horaFin1: "", horaInicio2: "", horaFin2: "" };
}

export default function HorariosPageV2() {
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
      map[hor.usuarioId] = { label: hor.label, horaInicio1: hor.horaInicio1 ?? "", horaFin1: hor.horaFin1 ?? "", horaInicio2: hor.horaInicio2 ?? "", horaFin2: hor.horaFin2 ?? "" };
    }
    setForms(map);
    setLoading(false);
  };

  useEffect(() => { if (token && canAccess) cargar(); }, [token, mes, anio, canAccess]);

  const guardar = async (usuarioId: number) => {
    if (!token) return;
    const f = forms[usuarioId];
    const label = f?.label?.trim() || [f?.horaInicio1 && f?.horaFin1 ? `${f.horaInicio1}-${f.horaFin1}` : "", f?.horaInicio2 && f?.horaFin2 ? `${f.horaInicio2}-${f.horaFin2}` : ""].filter(Boolean).join(" + ") || "Sin horario";
    try {
      await api("/horarios", token, { method: "POST", body: JSON.stringify({ ...f, label, usuarioId, mes, anio }) });
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
      const label = f.label?.trim() || [f.horaInicio1 && f.horaFin1 ? `${f.horaInicio1}-${f.horaFin1}` : "", f.horaInicio2 && f.horaFin2 ? `${f.horaInicio2}-${f.horaFin2}` : ""].filter(Boolean).join(" + ") || "Sin horario";
      try { await api("/horarios", token, { method: "POST", body: JSON.stringify({ ...f, label, usuarioId: t.id, mes, anio }) }); ok++; } catch { err++; }
    }
    setGuardando(false); setEditando(null);
    if (err === 0) toast(`Todos los horarios guardados (${ok})`, "success");
    else toast(`${ok} guardados, ${err} errores`, "error");
    const c = await api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
    setCobertura((c as any).cobertura ?? []);
  };

  const aplicarPlantilla = (usuarioId: number, p: typeof PLANTILLAS[number]) => {
    setForms((prev) => ({ ...prev, [usuarioId]: { label: p.label, horaInicio1: p.h1, horaFin1: p.f1, horaInicio2: p.h2, horaFin2: p.f2 } }));
  };

  const limpiar = async (usuarioId: number) => {
    if (!token) return;
    try {
      const h = await api(`/horarios?mes=${mes}&anio=${anio}`, token).then((r) => r.json()) as any[];
      const hor = h.find((x: any) => x.usuarioId === usuarioId);
      if (hor?.id) { await api(`/horarios/${hor.id}`, token, { method: "DELETE" }); toast("Horario eliminado", "info"); }
      setForms((prev) => { const n = { ...prev }; delete n[usuarioId]; return n; });
      const c = await api(`/horarios/cobertura?mes=${mes}&anio=${anio}`, token).then((r) => r.json());
      setCobertura((c as any).cobertura ?? []);
    } catch {}
  };

  if (!user || !canAccess) return null;

  const s = { bg: "#f2f0eb", accent: "#00754A", house: "#1e3932", cream: "#faf6ee", gold: "#cba258", border: "#e7e7e7" } as const;

  return (
    <main style={{ background: s.bg, minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "-0.01em" }}>
      <div style={{ background: s.house, color: "#fff", padding: "22px 0 18px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
          <h1 style={{ fontSize: "clamp(22px,3vw,28px)", letterSpacing: "-0.03em", fontWeight: 700 }}>Gestión de Horarios</h1>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>Asigna los horarios del equipo para {MONTHS[mes - 1]} {anio}</p>
        </div>
      </div>

      <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px 40px" }}>
        <select value={mes} onChange={(e) => setMes(Number(e.target.value))} style={{ borderRadius: 9999, padding: "8px 16px", fontSize: 13, fontWeight: 600, background: "#fff", color: "#1e3932", border: "1px solid #d6dbde", cursor: "pointer", marginTop: 24 }}>
          {MONTHS.map((m, i) => (<option key={i} value={i + 1}>{m}</option>))}
        </select>

        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginTop: 24 }}>
            {[1,2,3].map(i => <div key={i} style={{ height: 60, borderRadius: 12, background: "#edebe9", opacity: 0.5 }} />)}
          </div>
        ) : (
          <>
            {/* Horarios */}
            <div style={{ background: "#fff", border: `1px solid ${s.border}`, borderRadius: 12, marginTop: 16, padding: 16 }}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                {PLANTILLAS.map((p) => (
                  <button key={p.label} onClick={() => { if (editando !== null) aplicarPlantilla(editando, p); }} disabled={editando === null}
                    style={{ borderRadius: 9999, padding: "6px 12px", fontSize: 11, fontWeight: 600, background: editando !== null ? "#f2f0eb" : "#fff", color: editando !== null ? "#1e3932" : "rgba(0,0,0,0.4)", border: "1px solid #e7e7e7", cursor: editando !== null ? "pointer" : "default", opacity: editando !== null ? 1 : 0.5 }}>
                    {p.label}
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontSize: 11, color: "rgba(0,0,0,0.58)" }}>
                  {tecnicos.filter((t) => forms[t.id]?.horaInicio1).length} de {tecnicos.length} técnicos con horario
                </span>
                <button onClick={guardarTodo} disabled={guardando} style={{ borderRadius: 9999, padding: "6px 14px", fontSize: 12, fontWeight: 700, background: guardando ? "#d6dbde" : s.accent, color: "#fff", border: "none", cursor: guardando ? "default" : "pointer" }}>
                  {guardando ? "Guardando..." : "Guardar todo"}
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {tecnicos.map((t) => {
                  const f = forms[t.id];
                  const activo = editando === t.id;
                  return (
                    <div key={t.id} style={{ border: `1.5px solid ${activo ? "#00754A" : "#e7e7e7"}`, borderRadius: 12, padding: 12, background: activo ? "#f9f9f9" : "#fff" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#1e3932" }}>{t.displayName}</span>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          {f?.label && !activo && <span style={{ fontSize: 11, color: "rgba(0,0,0,0.58)" }}>{f.label}</span>}
                          <button onClick={() => setEditando(activo ? null : t.id)} style={{ borderRadius: 8, padding: "4px 10px", fontSize: 11, fontWeight: 600, background: activo ? "transparent" : "#f2f0eb", color: activo ? s.accent : "#1e3932", border: "none", cursor: "pointer" }}>
                            {activo ? "Cancelar" : f?.label ? "Editar" : "Asignar"}
                          </button>
                          {f?.label && (
                            <button onClick={() => limpiar(t.id)} style={{ borderRadius: 8, padding: "4px 8px", fontSize: 11, background: "transparent", border: "none", color: "#c82014", cursor: "pointer" }}>✕</button>
                          )}
                        </div>
                      </div>
                      {activo && (
                        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                            <span style={{ width: 64, color: "rgba(0,0,0,0.58)" }}>Bloque 1</span>
                            <input type="time" value={f?.horaInicio1 ?? ""} onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaInicio1: e.target.value } }))}
                              style={{ borderRadius: 4, border: "1.5px solid #d6dbde", padding: "4px 8px", fontSize: 12 }} />
                            <span style={{ color: "rgba(0,0,0,0.4)" }}>a</span>
                            <input type="time" value={f?.horaFin1 ?? ""} onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaFin1: e.target.value } }))}
                              style={{ borderRadius: 4, border: "1.5px solid #d6dbde", padding: "4px 8px", fontSize: 12 }} />
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                            <span style={{ width: 64, color: "rgba(0,0,0,0.58)" }}>Bloque 2</span>
                            <input type="time" value={f?.horaInicio2 ?? ""} onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaInicio2: e.target.value } }))}
                              style={{ borderRadius: 4, border: "1.5px solid #d6dbde", padding: "4px 8px", fontSize: 12 }} />
                            <span style={{ color: "rgba(0,0,0,0.4)" }}>a</span>
                            <input type="time" value={f?.horaFin2 ?? ""} onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), horaFin2: e.target.value } }))}
                              style={{ borderRadius: 4, border: "1.5px solid #d6dbde", padding: "4px 8px", fontSize: 12 }} />
                            <span style={{ fontSize: 10, color: "rgba(0,0,0,0.4)" }}>(opcional)</span>
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <input type="text" value={f?.label ?? ""} onChange={(e) => setForms((p) => ({ ...p, [t.id]: { ...(p[t.id] ?? emptyForm()), label: e.target.value } }))}
                              placeholder="Comentario (opcional)" style={{ flex: 1, borderRadius: 4, border: "1.5px solid #d6dbde", padding: "4px 8px", fontSize: 12 }} />
                            <button onClick={() => guardar(t.id)} style={{ borderRadius: 9999, padding: "6px 14px", fontSize: 12, fontWeight: 700, background: s.accent, color: "#fff", border: "none", cursor: "pointer" }}>Guardar</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Cobertura */}
            <div style={{ background: "#fff", border: `1px solid ${s.border}`, borderRadius: 12, marginTop: 16, padding: 16 }}>
              <h2 style={{ fontSize: 13, fontWeight: 700, color: "#1e3932", marginBottom: 12 }}>Cobertura — {MONTHS[mes - 1]} {anio}</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
                {cobertura.map((c) => (
                  <div key={c.franja} style={{ border: `1px solid ${s.border}`, borderRadius: 12, padding: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#1e3932" }}>{c.franja}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: s.gold, letterSpacing: "0.04em" }}>{c.hora}</span>
                    </div>
                    {c.tecnicos.length === 0 ? (
                      <p style={{ marginTop: 8, fontSize: 12, color: "rgba(0,0,0,0.58)" }}>Sin cobertura</p>
                    ) : (
                      <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {c.tecnicos.map((nom) => (
                          <span key={nom} style={{ fontSize: 11, fontWeight: 600, padding: "4px 8px", borderRadius: 9999, background: "#f2f0eb", color: "#1e3932", display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#00754A", display: "inline-block" }} />
                            {nom}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
