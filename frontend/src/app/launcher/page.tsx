"use client";

import { useState } from "react";
import Link from "next/link";

const USERS = [
  { id: "u1", name: "M. Valdez", role: "Jefe", sistema: "AMBOS" },
  { id: "u2", name: "C. Mendoza", role: "Jefe", sistema: "AMBOS" },
  { id: "u3", name: "J. Ramos", role: "Tecnico", sistema: "SOPORTE" },
  { id: "u4", name: "A. Paredes", role: "Tecnico", sistema: "SOPORTE" },
  { id: "u5", name: "L. Soto", role: "Tecnico", sistema: "AUXILIARES" },
  { id: "u6", name: "D. Flores", role: "Tecnico", sistema: "AUXILIARES" },
];

interface CardData {
  href: string;
  topColor: string;
  kicker: string;
  title: string;
  desc: string;
  chips: string[];
  roles: string[];
}

const CARDS: CardData[] = [
  { href: "/dashboard", topColor: "#1e3932", kicker: "Jefe", title: "Dashboard", desc: "KPIs por GrupoPadre, área, técnico y mes. Filtros jerárquicos.", chips: ["porGrupoPadre", "porArea 53", "porTecnico", "porMes"], roles: ["Jefe"] },
  { href: "/soporte", topColor: "#00754A", kicker: "Todos", title: "Soporte", desc: "Registrar atenciones con cascada 3 niveles: GrupoPadre → Grupo → Área (53).", chips: ["JerarquiaSelector", "Batch", "Sugerencias"], roles: ["Jefe", "Tecnico"] },
  { href: "/reporte", topColor: "#006241", kicker: "Jefe", title: "Reportes", desc: "Exportar datos por sistema (Soporte/Auxiliares) e jerarquía.", chips: ["CSV", "PDF", "Independiente"], roles: ["Jefe"] },
  { href: "/horarios", topColor: "#cba258", kicker: "Jefe", title: "Horarios", desc: "Gestión de turnos, plantillas rápidas y cobertura.", chips: ["Plantillas", "Cobertura"], roles: ["Jefe"] },
  { href: "/perfil/1", topColor: "#4f46e5", kicker: "Todos", title: "Perfil", desc: "Métricas personales, ranking, logros y rendimiento mensual.", chips: ["Ranking", "Badges", "Barras"], roles: ["Jefe", "Tecnico"] },
  { href: "/soporte", topColor: "#1e3932", kicker: "Auxiliares", title: "Auxiliares", desc: "Sistema paralelo para áreas externas. Toggle solo Jefe AMBOS.", chips: ["Sistema auto", "Independiente"], roles: ["Jefe"] },
];

export default function LauncherPage() {
  const [user, setUser] = useState(USERS[0]);

  const filteredCards = CARDS.filter(c => c.roles.includes(user.role));

  return (
    <main style={{ background: "#f2f0eb", minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "-0.01em" }}>
      {/* Hero */}
      <div style={{ background: "#1e3932", color: "#fff", padding: "32px 0 24px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
          <Link href="/" style={{ display: "inline-block", marginBottom: 12, padding: "4px 10px", fontSize: 11, fontWeight: 600, background: "rgba(255,255,255,0.1)", borderRadius: 9999, border: "1px solid rgba(255,255,255,0.18)", color: "#fff", textDecoration: "none" }}>← Dashboard</Link>
          <p style={{ fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", fontWeight: 700, color: "rgba(255,255,255,0.6)", marginBottom: 6 }}>Prototipo V2</p>
          <h1 style={{ fontSize: "clamp(26px,4vw,42px)", lineHeight: 1.05, letterSpacing: "-0.03em", fontWeight: 700, maxWidth: 820 }}>Soporte Técnico — UPDS</h1>
          <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.6, color: "rgba(255,255,255,0.72)", maxWidth: 720 }}>Sistema de registro de atenciones con jerarquía 3 niveles, Starbucks Design System y mock data.</p>
          <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 6 }}>
            <span style={{ borderRadius: 9999, padding: "4px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.9)" }}>Starbucks DS <strong>#00754A</strong></span>
            <span style={{ borderRadius: 9999, padding: "4px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.9)" }}>53 áreas · 3 GrupoPadre</span>
            <span style={{ borderRadius: 9999, padding: "4px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.9)" }}>Pill 50px</span>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
        {/* Controls */}
        <div style={{ marginTop: 20, background: "#fff", border: "1px solid #e7e7e7", borderRadius: 16, padding: 16, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Usuario</span>
            <select value={user.id} onChange={(e) => setUser(USERS.find(u => u.id === e.target.value) || USERS[0])}
              style={{ borderRadius: 9999, padding: "6px 14px", fontSize: 13, fontWeight: 600, background: "#f2f0eb", color: "#1e3932", border: "1px solid #e7e7e7", cursor: "pointer" }}>
              {USERS.map(u => <option key={u.id} value={u.id}>{u.name} ({u.role} · {u.sistema})</option>)}
            </select>
          </div>
          <span style={{ marginLeft: "auto", borderRadius: 9999, padding: "4px 10px", fontSize: 11, fontWeight: 700, background: "#1e3932", color: "#fff" }}>{user.sistema}</span>
        </div>

        {/* Cards */}
        <div style={{ padding: "24px 0 48px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 18 }}>
          {filteredCards.map((card) => (
            <Link key={card.title} href={card.href}
              style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 16, overflow: "hidden", boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", display: "flex", flexDirection: "column", transition: "transform 0.18s", textDecoration: "none", color: "inherit" }}>
              <div style={{ height: 8, background: card.topColor }} />
              <div style={{ padding: "16px 18px 18px", flex: 1, display: "flex", flexDirection: "column" }}>
                <div style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 700, color: "#00754A", marginBottom: 4 }}>{card.kicker}</div>
                <h2 style={{ fontSize: 17, lineHeight: 1.2, fontWeight: 700, letterSpacing: "-0.02em", color: "#1e3932" }}>{card.title}</h2>
                <p style={{ marginTop: 6, fontSize: 13, lineHeight: 1.5, color: "rgba(0,0,0,0.58)" }}>{card.desc}</p>
                <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {card.chips.map(c => (
                    <span key={c} style={{ fontSize: 11, fontWeight: 600, padding: "4px 8px", borderRadius: 9999, border: "1px solid #d6dbde", background: "#fff", color: "#33433d" }}>{c}</span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Spec tokens */}
        <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: "16px 20px", marginBottom: 40 }}>
          <h3 style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)", marginBottom: 10 }}>Tokens Starbucks</h3>
          {[
            ["accent", "#00754A", "CTA fill + focus ring"],
            ["house", "#1e3932", "Feature bands / hero"],
            ["starbucks", "#006241", "Headings / logo"],
            ["gold", "#cba258", "Rewards / fueraDeTurno"],
            ["cream", "#faf6ee", "Card surface"],
            ["bg", "#f2f0eb", "Page canvas"],
          ].map(([name, hex, desc]) => (
            <div key={name} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f5f3f0", fontSize: 12 }}>
              <span style={{ color: "rgba(0,0,0,0.58)", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 14, height: 14, borderRadius: 3, background: hex, display: "inline-block", border: "1px solid rgba(0,0,0,0.1)" }} />
                {name}
              </span>
              <span style={{ fontWeight: 600 }}>{hex} — {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
