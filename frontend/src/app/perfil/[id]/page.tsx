"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDashboardStats, getUsuarios } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import type { DashboardStats } from "@/lib/api";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function PerfilPageV2() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [globalStats, setGlobalStats] = useState<DashboardStats | null>(null);
  const [horario, setHorario] = useState<{ label: string; horaInicio1: string; horaFin1: string; horaInicio2?: string; horaFin2?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    const uid = Number(id);
    if (isNaN(uid)) { router.replace("/dashboard"); return; }
    const now = new Date();
    const mes = now.getMonth() + 1;
    const anio = now.getFullYear();
    const token = localStorage.getItem("auth_token") || sessionStorage.getItem("auth_token");
    const hostname = window.location.hostname;

    Promise.all([
      getDashboardStats({ usuarioId: uid }),
      getDashboardStats(),
      token ? fetch(`http://${hostname}:5001/api/horarios?mes=${mes}&anio=${anio}`, {
        headers: { Authorization: `Bearer ${token}` }
      }).then(r => r.json()).then(h => {
        const miHorario = (h as any[]).find((x: any) => x.usuarioId === uid);
        if (miHorario) setHorario(miHorario);
      }) : Promise.resolve(),
    ]).then(([s, g]) => { setStats(s); setGlobalStats(g); })
      .finally(() => setLoading(false));
  }, [id, user, router]);

  if (loading || !stats || !globalStats) {
    return (
      <div style={{ background: "#f2f0eb", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter, system-ui, sans-serif" }}>
        <span style={{ fontSize: 13, color: "rgba(0,0,0,0.58)" }}>Cargando perfil...</span>
      </div>
    );
  }

  const uid = Number(id);
  const tecnico = stats.porTecnico[0];
  if (!tecnico) return <p style={{ padding: 24, textAlign: "center", color: "rgba(0,0,0,0.58)" }}>Técnico no encontrado</p>;

  const nombre = tecnico.displayName;
  const iniciales = nombre.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  const total = tecnico.total;
  const estrellas = Math.floor(total / 100);
  const promedio = Math.round(total / (stats.porMes.length || 1));
  const rankingPos = globalStats.porTecnico.findIndex((t) => t.usuarioId === uid) + 1;
  const totalGlobal = globalStats.total || 1;
  const pctEquipo = ((total / totalGlobal) * 100).toFixed(1);
  const promedioEquipo = Math.round(totalGlobal / (globalStats.porTecnico.length || 1));
  const difPromedio = total - promedioEquipo;

  let especialidad = "General";
  let especialidadCount = 0;
  for (const c of stats.porCategoria) {
    if (c.total > especialidadCount) { especialidadCount = c.total; especialidad = c.categoria; }
  }

  const badges: { label: string; desc: string; bg: string; color: string }[] = [];
  if (rankingPos === 1) badges.push({ label: "🥇", desc: "Líder del equipo", bg: "linear-gradient(135deg,#f59e0b,#d97706)", color: "#fff" });
  if (total >= 100) badges.push({ label: "💪", desc: "100+ atenciones", bg: "linear-gradient(135deg,#00754A,#1e3932)", color: "#fff" });
  if (especialidadCount > 0) badges.push({ label: "🎯", desc: `Especialista en ${especialidad}`, bg: "#f2f0eb", color: "#1e3932" });
  if (stats.porMes.length >= 5) badges.push({ label: "📅", desc: "Constante todos los meses", bg: "#f2f0eb", color: "#1e3932" });
  if (promedio >= 30) badges.push({ label: "⚡", desc: "Alto rendimiento", bg: "linear-gradient(135deg,#00754A,#1e3932)", color: "#fff" });

  const maxCat = Math.max(...stats.porCategoria.map((c) => c.total), 1);
  const maxMes = Math.max(...stats.porMes.map((m) => m.total), 1);

  const s = { bg: "#f2f0eb", accent: "#00754A", house: "#1e3932", cream: "#faf6ee", gold: "#cba258", border: "#e7e7e7" } as const;
  const cardStyle = { background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: 16, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)" } as const;

  return (
    <main style={{ background: s.bg, minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "-0.01em" }}>
      {/* Header */}
      <div style={{ background: s.house, color: "#fff", padding: "22px 0 18px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px", display: "flex", alignItems: "center", gap: 16 }}>
          <button onClick={() => router.back()} style={{ borderRadius: 9999, padding: "6px 14px", fontSize: 12, fontWeight: 600, background: "rgba(255,255,255,0.1)", color: "#fff", border: "1px solid rgba(255,255,255,0.18)", cursor: "pointer" }}>← Volver</button>
          <div>
            <h1 style={{ fontSize: "clamp(20px,3vw,26px)", letterSpacing: "-0.03em", fontWeight: 700 }}>Perfil</h1>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>Métricas personales por jerarquía</p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 40px 40px" }}>
        {/* Avatar + info */}
        <div style={{ ...cardStyle, marginTop: 24, display: "flex", flexDirection: "column", alignItems: "center", padding: 24, gap: 16 }}>
          <div style={{ width: 72, height: 72, borderRadius: 16, background: "linear-gradient(135deg,#00754A,#1e3932)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 700, color: "#fff" }}>{iniciales}</div>
          <div style={{ textAlign: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }}>
              <span style={{ fontSize: 18, fontWeight: 700, color: "#1e3932" }}>{nombre}</span>
              {estrellas > 0 && <span style={{ color: "#cba258", fontSize: 16 }}>{String.fromCodePoint(0x2605).repeat(estrellas)}</span>}
            </div>
            <p style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)", marginTop: 4 }}>
              Técnico · {rankingPos === 1 ? "Líder del equipo" : `#${rankingPos} en ranking`}
            </p>
          </div>
          {horario && (
            <div style={{ background: "#f2f0eb", borderRadius: 8, padding: "8px 14px", fontSize: 12, color: "#1e3932", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Horario</span>
              <span style={{ fontWeight: 600 }}>{horario.label}</span>
            </div>
          )}
        </div>

        {/* Stats 4 cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginTop: 16 }}>
          <div style={{ ...cardStyle, textAlign: "center" }}><p style={{ fontSize: 22, fontWeight: 800, color: s.accent }}>{total}</p><p style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Atenciones</p></div>
          <div style={{ ...cardStyle, textAlign: "center" }}><p style={{ fontSize: 22, fontWeight: 800, color: s.house }}>{promedio}</p><p style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Promedio/Mes</p></div>
          <div style={{ ...cardStyle, textAlign: "center" }}><p style={{ fontSize: 22, fontWeight: 800, color: s.accent }}>#{rankingPos}</p><p style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Posición</p></div>
          <div style={{ ...cardStyle, textAlign: "center" }}><p style={{ fontSize: 22, fontWeight: 800, color: difPromedio >= 0 ? s.accent : "#c82014" }}>{difPromedio > 0 ? `+${difPromedio}` : difPromedio}</p><p style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>vs Promedio</p></div>
        </div>

        {/* Contribución + Especialidad */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
          <div style={cardStyle}>
            <h3 style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)", marginBottom: 10 }}>Contribución al Equipo</h3>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: s.accent }}>{pctEquipo}%</span>
              <p style={{ fontSize: 11, color: "rgba(0,0,0,0.58)", marginTop: 4 }}>{total} de {totalGlobal}</p>
              <div style={{ marginTop: 10, height: 8, borderRadius: 9999, background: "#edebe9", overflow: "hidden" }}>
                <div style={{ height: "100%", borderRadius: 9999, background: s.accent, width: `${pctEquipo}%`, transition: "width 0.6s" }} />
              </div>
            </div>
          </div>
          <div style={cardStyle}>
            <h3 style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)", marginBottom: 10 }}>Especialidad</h3>
            <p style={{ fontSize: 16, fontWeight: 700, color: s.accent }}>{especialidad}</p>
            <p style={{ fontSize: 11, color: "rgba(0,0,0,0.58)", marginTop: 2 }}>{especialidadCount} atenciones</p>
            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
              {stats.porCategoria.slice(0, 4).map((c) => (
                <div key={c.categoria} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                  <span style={{ width: 16, fontWeight: 500, color: "#1e3932", textAlign: "right" }}>{c.total}</span>
                  <span style={{ flex: 1, color: "rgba(0,0,0,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.categoria}</span>
                  <div style={{ width: 80, height: 6, borderRadius: 9999, background: "#edebe9", overflow: "hidden" }}>
                    <div style={{ height: "100%", borderRadius: 9999, background: s.accent, width: `${(c.total / maxCat) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Badges */}
        {badges.length > 0 && (
          <div style={cardStyle}>
            <h3 style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)", marginBottom: 12 }}>Logros</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {badges.map((b) => (
                <div key={b.label} style={{ background: b.bg, color: b.color, borderRadius: 12, padding: "8px 14px", fontSize: 12, fontWeight: 600, display: "flex", alignItems: "center", gap: 6, boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
                  <span style={{ fontSize: 16 }}>{b.label}</span>{b.desc}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mini gráfico mensual */}
        <div style={cardStyle}>
          <h3 style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)", marginBottom: 12 }}>Rendimiento Mensual</h3>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 100 }}>
            {stats.porMes.map((m) => (
              <div key={`${m.anio}-${m.mes}`} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: "#1e3932" }}>{m.total}</span>
                <div style={{ width: "100%", borderRadius: "4px 4px 0 0", background: "linear-gradient(to top,#00754A,#1e3932)", height: `${(m.total / maxMes) * 60}px`, minHeight: m.total > 0 ? 3 : 0, transition: "height 0.4s" }} />
                <span style={{ fontSize: 9, color: "rgba(0,0,0,0.58)" }}>{MONTHS[m.mes - 1]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
