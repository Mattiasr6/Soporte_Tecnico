"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { getDashboardStats, getUsuarios, type DashboardStats } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function ReportePageV2() {
  const { user } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const printRef = useRef<HTMLDivElement>(null);

  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) router.replace("/soporte");
  }, [user, canAccess, router]);

  useEffect(() => {
    if (!canAccess) return;
    setLoading(true);
    getDashboardStats({ desdeMes: 1, desdeAnio: 2026, hastaMes: 8, hastaAnio: 2026 })
      .then(setStats)
      .finally(() => setLoading(false));
  }, [canAccess]);

  const handlePrint = () => {
    if (!printRef.current) return;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`<html><head><title>Reporte</title><style>body{font-family:Inter,sans-serif;padding:40px;color:#1a1a1a}table{width:100%;border-collapse:collapse;margin-top:16px}th,td{border:1px solid #e5e7eb;padding:8px 12px;text-align:left;font-size:13px}th{background:#f9fafb;font-weight:600}.h1{color:#006241}.h2{color:#1e3932}h1,h2{margin:0}</style></head><body>`);
    w.document.write(printRef.current.innerHTML);
    w.document.write("</body></html>");
    w.document.close();
    w.print();
  };

  if (!user || !canAccess) return null;

  return (
    <main style={{ background: "#f2f0eb", minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "-0.01em" }}>
      {/* Header */}
      <div style={{ background: "#1e3932", color: "#fff", padding: "22px 0 18px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
          <h1 style={{ fontSize: "clamp(22px,3vw,28px)", letterSpacing: "-0.03em", fontWeight: 700 }}>Reportes V2</h1>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>Exporta datos por sistema (Soporte/Auxiliares) e jerarquía</p>
        </div>
      </div>

      <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
        {/* KPIs */}
        <div ref={printRef} style={{ marginTop: 24 }}>
          {loading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
              {[1,2,3,4].map(i => <div key={i} style={{ height: 80, borderRadius: 12, background: "#edebe9", opacity: 0.5 }} />)}
            </div>
          ) : stats && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: 16, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)" }}>
                <div style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Total Atenciones</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#1e3932", marginTop: 4 }}>{stats.total}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Fuera de Turno</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#cba258", marginTop: 4 }}>{stats.fueraDeTurno}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Técnicos</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#1e3932", marginTop: 4 }}>{stats.porTecnico.length}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, color: "rgba(0,0,0,0.58)" }}>Áreas</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#1e3932", marginTop: 4 }}>{stats.porArea.length}</div>
              </div>
            </div>
          )}

          {/* Tabla por Técnico */}
          {stats && (
            <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, marginTop: 16, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Técnico</th>
                    <th style={{ textAlign: "right", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Atenciones</th>
                    <th style={{ textAlign: "right", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>%</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.porTecnico.map((t, i) => (
                    <tr key={i}>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0", fontWeight: 500 }}>{t.displayName}</td>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0", textAlign: "right", fontWeight: 700 }}>{t.total}</td>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0", textAlign: "right", color: "rgba(0,0,0,0.58)" }}>{stats.total > 0 ? ((t.total / stats.total) * 100).toFixed(1) : 0}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tabla por Área */}
          {stats && (
            <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, marginTop: 16, overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid #f0ede8", fontSize: 13, fontWeight: 700, color: "#1e3932" }}>Por Área (jerarquía)</div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Área</th>
                    <th style={{ textAlign: "right", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.porArea.slice(0, 20).map((a, i) => (
                    <tr key={i}>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0" }}>{a.area}</td>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0", textAlign: "right", fontWeight: 700 }}>{a.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tabla por Categoría */}
          {stats && (
            <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, marginTop: 16, overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid #f0ede8", fontSize: 13, fontWeight: 700, color: "#1e3932" }}>Por Categoría</div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Categoría</th>
                    <th style={{ textAlign: "right", padding: "10px 12px", background: "#f2f0eb", borderBottom: "1px solid #f0ede8", fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(0,0,0,0.58)" }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.porCategoria.map((c, i) => (
                    <tr key={i}>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0" }}>{c.categoria}</td>
                      <td style={{ padding: "10px 12px", borderBottom: "1px solid #f5f3f0", textAlign: "right", fontWeight: 700 }}>{c.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Botones */}
        <div style={{ display: "flex", gap: 10, margin: "24px 0 40px", justifyContent: "flex-end" }}>
          <button onClick={handlePrint} style={{ borderRadius: 9999, padding: "8px 16px", fontSize: 13, fontWeight: 600, background: "#00754A", color: "#fff", border: "none", cursor: "pointer" }}>Imprimir PDF</button>
          {stats && (
            <button onClick={() => {
              const csv = [
                "Técnico,Atenciones",
                ...stats.porTecnico.map(t => `${t.displayName},${t.total}`),
                "",
                "Área,Total",
                ...stats.porArea.map(a => `${a.area},${a.total}`),
                "",
                "Categoría,Total",
                ...stats.porCategoria.map(c => `${c.categoria},${c.total}`),
              ].join("\n");
              const blob = new Blob([csv], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url; a.download = "reporte_v2.csv"; a.click();
              URL.revokeObjectURL(url);
            }} style={{ borderRadius: 9999, padding: "8px 16px", fontSize: 13, fontWeight: 600, background: "transparent", color: "#1e3932", border: "1px solid #d6dbde", cursor: "pointer" }}>Exportar CSV</button>
          )}
        </div>
      </div>
    </main>
  );
}
