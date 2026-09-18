"use client";

import { useState } from "react";
import type { JerarquiaSelection } from "@/types";
import JerarquiaSelector from "@/components/JerarquiaSelector";
import AtencionTableV2 from "@/components/AtencionTableV2";

const INITIAL_SEL: JerarquiaSelection = { padre: null, grupo: null, area: null };

export default function SoportePage() {
  const [jerarquia, setJerarquia] = useState<JerarquiaSelection>(INITIAL_SEL);

  const step =
    (jerarquia.padre ? 1 : 0) +
    (jerarquia.grupo ? 1 : 0) +
    (jerarquia.area ? 1 : 0);

  return (
    <div style={{ background: "#f2f0eb", minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "-0.01em" }}>
      {/* Band Starbucks */}
      <header style={{ background: "#1e3932", color: "#fff", padding: "24px 0 20px" }}>
        <div style={{ maxWidth: 1440, margin: "0 auto", padding: "0 40px" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)" }}>Nuevo registro</span>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)" }}>53 áreas exactas</span>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <iconify-icon icon="mdi:source-branch" width="14" />
              cascada real
            </span>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <iconify-icon icon="mdi:map-marker-multiple" width="14" />
              53 áreas
            </span>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <iconify-icon icon="mdi:format-list-bulleted" width="14" />
              batch múltiple
            </span>
            <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)", display: "inline-flex", alignItems: "center", gap: 6 }}>
              <iconify-icon icon="mdi:check-circle" width="14" />
              validación 3 niveles
            </span>
          </div>
          <h1 style={{ fontSize: "clamp(22px,3vw,30px)", lineHeight: 1.15, letterSpacing: "-0.03em", fontWeight: 700 }}>
            Registrar atención con jerarquía exacta — 3 pasos, sin error.
          </h1>
          <p style={{ marginTop: 8, color: "rgba(255,255,255,0.7)", fontSize: 13, maxWidth: 720, lineHeight: 1.6 }}>
            Selecciona GrupoPadre → Grupo → Área filtrada. El breadcrumb 1–3 chips confirma la ruta antes del batch.
          </p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["cascada real", "53 áreas", "batch múltiple", "validación 3 niveles"].map(b => (
              <span key={b} style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.08)" }}>{b}</span>
            ))}
          </div>
        </div>
      </header>

      {/* Main */}
      <div style={{ maxWidth: 1440, margin: "0 auto", padding: "20px 40px 40px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
          {/* @media min-width:1100px → grid-template-columns: minmax(0,1fr) 360px */}
          <div style={{ display: "grid", gap: 22, alignItems: "start", gridTemplateColumns: "minmax(0,1fr) 360px" }}>
            {/* Left: JerarquiaSelector + AtencionTableV2 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {/* JerarquiaSelector */}
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", overflow: "hidden" }}>
                <div style={{ padding: "16px 18px 14px", borderBottom: "1px solid #f0ede8", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h2 style={{ fontSize: 14, fontWeight: 700, color: "#1e3932", letterSpacing: "-0.02em" }}>JerarquiaSelector — 3 niveles</h2>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    {[1,2,3].map(i => (
                      <span key={i} style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 700, border: `1.5px solid ${step >= i ? "#00754A" : "#d6dbde"}`, background: step >= i ? "#00754A" : "#fff", color: step >= i ? "#fff" : "rgba(0,0,0,0.5)" }}>{i}</span>
                    ))}
                  </div>
                </div>
                <div style={{ padding: 16 }}>
                  <JerarquiaSelector value={jerarquia} onChange={setJerarquia} />
                </div>
              </div>

              {/* AtencionTableV2 */}
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", overflow: "hidden" }}>
                <div style={{ padding: "16px 18px 14px", borderBottom: "1px solid #f0ede8", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h2 style={{ fontSize: 14, fontWeight: 700, color: "#1e3932", letterSpacing: "-0.02em" }}>Datos de la atención</h2>
                  <span style={{ fontSize: 11, color: "rgba(0,0,0,0.58)" }}>Se guardan como nombres legibles</span>
                </div>
                <div style={{ padding: 16 }}>
                  <AtencionTableV2 jerarquia={jerarquia} />
                </div>
              </div>
            </div>

            {/* Right sidebar */}
            <aside style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Ruta actual */}
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", padding: 16 }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: "#1e3932", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
                  <iconify-icon icon="mdi:map" width="16" /> Ruta actual
                </h4>
                {jerarquia.padre ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#1e3932" }} />
                      <span style={{ fontSize: 13, fontWeight: 700, color: "#1e3932" }}>{jerarquia.padre.nombre}</span>
                      <span style={{ marginLeft: "auto", fontSize: 11, color: "rgba(0,0,0,0.58)" }}>GrupoPadre</span>
                    </div>
                    {jerarquia.grupo && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#00754A" }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: "#1e3932" }}>{jerarquia.grupo.nombre}</span>
                        <span style={{ marginLeft: "auto", fontSize: 11, color: "rgba(0,0,0,0.58)" }}>Grupo</span>
                      </div>
                    )}
                    {jerarquia.area && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#cba258" }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: "#1e3932" }}>{jerarquia.area.nombre}</span>
                        <span style={{ marginLeft: "auto", fontSize: 11, color: "rgba(0,0,0,0.58)" }}>Área</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p style={{ borderRadius: 8, background: "#f2f0eb", padding: 12, textAlign: "center", fontSize: 13, color: "rgba(0,0,0,0.58)" }}>Selecciona Padre → Grupo → Área</p>
                )}
                <div style={{ marginTop: 12, height: 8, borderRadius: 9999, background: "#e7e7e7", overflow: "hidden" }}>
                  <div style={{ height: "100%", borderRadius: 9999, background: "#00754A", width: `${(step / 3) * 100}%`, transition: "width 0.3s" }} />
                </div>
                <div style={{ marginTop: 6, display: "flex", justifyContent: "space-between", fontSize: 11, color: "rgba(0,0,0,0.58)" }}>
                  <span>Progreso jerarquía</span>
                  <span style={{ fontWeight: 700, color: "#00754A" }}>{step}/3</span>
                </div>
              </div>

              {/* Especificación */}
              <div style={{ background: "#fff", border: "1px solid #e7e7e7", borderRadius: 12, boxShadow: "0 0 0.5px rgba(0,0,0,.14),0 1px 1px rgba(0,0,0,.24)", padding: 16 }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: "#1e3932", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
                  <iconify-icon icon="mdi:filter-cog" width="16" /> Especificación de filtrado
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {[
                    ["GrupoPadre", "3 cards"],
                    ["Grupo (chips)", jerarquia.padre ? `${jerarquia.padre.grupos.length} según ${jerarquia.padre.nombre}` : "—"],
                    ["Área (combobox)", "53 totales"],
                    ["Breadcrumb", "1–3 chips"],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f5f3f0", fontSize: 12 }}>
                      <span style={{ color: "rgba(0,0,0,0.58)" }}>{k}</span>
                      <span style={{ fontWeight: 600, color: "#1e3932" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Batch */}
              <div style={{ background: "#1e3932", borderRadius: 12, padding: 16, color: "#fff" }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  <iconify-icon icon="mdi:lightning-bolt" width="16" /> Batch y validación
                </h4>
                <p style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.75 }}>
                  Solo se agrega si <strong style={{ color: "#fff" }}>descripción + solución + 3 niveles</strong> completos.
                </p>
                <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, background: "rgba(255,255,255,0.14)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <iconify-icon icon="mdi:map-marker-multiple" width="12" />53 áreas
                  </span>
                  <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, background: "rgba(255,255,255,0.14)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <iconify-icon icon="mdi:tag-multiple" width="12" />8 cats
                  </span>
                  <span style={{ borderRadius: 9999, padding: "5px 10px", fontSize: 11, background: "rgba(255,255,255,0.14)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <iconify-icon icon="mdi:transmission-tower" width="12" />4 medios
                  </span>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
