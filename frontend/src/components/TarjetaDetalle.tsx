"use client";

import type { AtencionItem } from "@/types";

// Starbucks tokens mapped to Tailwind classes
const S = {
  bg: "bg-[#f2f0eb]",
  surface: "bg-white",
  surfaceWarm: "bg-[#edebe9]",
  fg: "text-[rgba(0,0,0,0.87)]",
  fg2: "text-[#33433d]",
  muted: "text-[rgba(0,0,0,0.58)]",
  border: "border-[#d6dbde]",
  borderSoft: "border-[#e7e7e7]",
  accent: "bg-[#00754A]",
  accentText: "text-[#00754A]",
  accentOn: "text-white",
  danger: "bg-[#c82014]",
  dangerText: "text-[#c82014]",
  warn: "bg-[#fbbc05]",
  fontDisplay: "font-['SoDoSans',_'Helvetica_Neutral',_Helvetica,_Arial,_sans-serif]",
  fontBody: "font-['SoDoSans',_'Helvetica_Neutral',_Helvetica,_Arial,_sans-serif]",
  radiusMd: "rounded-xl",
  radiusSm: "rounded",
  shadowRaised: "shadow-[0_0_0.5px_0_rgba(0,0,0,0.14),0_1px_1px_0_rgba(0,0,0,0.24)]",
} as const;

type Props = {
  item: AtencionItem;
  onClose: () => void;
};

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className={`${S.muted} ${S.fontBody} text-xs tracking-tight uppercase block mb-0.5`}>
      {children}
    </span>
  );
}

function Value({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={`${S.fg} ${S.fontBody} text-sm leading-relaxed ${className}`}>
      {children || "—"}
    </p>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function Badge({ color, children }: { color: "green" | "red" | "amber" | "gray"; children: React.ReactNode }) {
  const map = {
    green: `${S.accent} ${S.accentOn}`,
    red: `${S.danger} text-white`,
    amber: "bg-[#fbbc05] text-[rgba(0,0,0,0.87)]",
    gray: `${S.surfaceWarm} ${S.fg2}`,
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 ${S.radiusSm} text-xs font-medium ${S.fontBody} ${map[color]}`}>
      {children}
    </span>
  );
}

function formatDate(iso: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-BO", { day: "2-digit", month: "short", year: "numeric" });
}

function formatDateTime(iso: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("es-BO", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function TarjetaDetalle({ item, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Card */}
      <div
        className={`relative ${S.surface} ${S.radiusMd} ${S.shadowRaised} w-full max-w-2xl max-h-[90vh] overflow-y-auto`}
      >
        {/* Header */}
        <div className={`sticky top-0 ${S.surface} z-10 px-6 pt-5 pb-3 border-b ${S.borderSoft}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <Badge color="green">{item.medioSolicitud}</Badge>
                {item.fueraDeTurno && <Badge color="red">Fuera de turno</Badge>}
              </div>
              <h2 className={`${S.fg} ${S.fontDisplay} text-lg font-semibold leading-tight truncate`}>
                {item.areaSolicitante}
              </h2>
              <p className={`${S.muted} ${S.fontBody} text-xs mt-0.5`}>
                #{item.id} &middot; {formatDate(item.fechaRegistro)}
              </p>
            </div>
            <button
              onClick={onClose}
              className={`${S.muted} hover:${S.fg} p-1 rounded transition-colors shrink-0`}
              aria-label="Cerrar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Solicitud */}
          <div className={`${S.surfaceWarm} ${S.radiusMd} p-4 space-y-3`}>
            <h3 className={`${S.fg2} ${S.fontDisplay} text-sm font-semibold uppercase tracking-tight`}>
              Solicitud
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Medio">{item.medioSolicitud}</Field>
              <Field label="Solicitante">{item.usuarioSolicitante}</Field>
              <Field label="Categoría">{item.categoria}</Field>
              <Field label="Área solicitante">{item.areaSolicitante}</Field>
            </div>
            <Field label="Descripción">
              <Value className="whitespace-pre-wrap">{item.descripcion}</Value>
            </Field>
          </div>

          {/* Solución */}
          <div className={`${S.surface} border ${S.borderSoft} ${S.radiusMd} p-4 space-y-3`}>
            <h3 className={`${S.fg2} ${S.fontDisplay} text-sm font-semibold uppercase tracking-tight`}>
              Solución
            </h3>
            <Field label="Resolución">
              <Value className="whitespace-pre-wrap">{item.solucion}</Value>
            </Field>
            {item.observaciones && (
              <Field label="Observaciones">
                <Value className="whitespace-pre-wrap">{item.observaciones}</Value>
              </Field>
            )}
            {item.enlaceApoyo && (
              <Field label="Enlace de apoyo">
                <a
                  href={item.enlaceApoyo}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`${S.accentText} text-sm underline underline-offset-2 hover:opacity-80 break-all`}
                >
                  {item.enlaceApoyo}
                </a>
              </Field>
            )}
          </div>

          {/* Técnico + Fechas */}
          <div className={`${S.surface} border ${S.borderSoft} ${S.radiusMd} p-4 space-y-3`}>
            <h3 className={`${S.fg2} ${S.fontDisplay} text-sm font-semibold uppercase tracking-tight`}>
              Técnico asignado
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Técnico">
                <Value>{item.colaboradorNombre || "Sin asignar"}</Value>
              </Field>
              <Field label="Atendido por">
                <Value>{item.usuarioNombre}</Value>
              </Field>
              <Field label="Fecha registro">
                <Value>{formatDateTime(item.fechaRegistro)}</Value>
              </Field>
              <Field label="Creado">
                <Value>{formatDateTime(item.createdAt)}</Value>
              </Field>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className={`sticky bottom-0 ${S.surface} border-t ${S.borderSoft} px-6 py-3 flex justify-end`}>
          <button
            onClick={onClose}
            className={`px-4 py-2 ${S.surfaceWarm} ${S.fg2} ${S.fontBody} text-sm font-medium ${S.radiusSm} hover:opacity-80 transition-opacity`}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
