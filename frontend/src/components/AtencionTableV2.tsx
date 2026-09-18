"use client";

import { useState, useEffect } from "react";
import type { JerarquiaSelection, AtencionBatchItem, Usuario } from "@/types";
import { useToast } from "./Toast";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api";

const MEDIOS = ["Presencial", "WhatsApp", "Teléfono", "Sistema"] as const;
const SOLICITANTES = [
  { value: "ADM", label: "ADM — Administrativo" },
  { value: "BEC", label: "BEC — Becario" },
  { value: "DOC", label: "DOC — Docente" },
  { value: "EST", label: "EST — Estudiante" },
] as const;
const CATEGORIAS = [
  "Hardware",
  "Software",
  "Red / Internet",
  "Impresora",
  "Correo",
  "Sistema Académico",
  "Usuario / Acceso",
  "Otros",
] as const;

const PLANTILLAS = [
  {
    key: "red",
    cat: "Red / Internet",
    desc: "Equipo sin conectividad cableada, puerto switch sin link. Verificar patch panel y VLAN.",
    sol: "Se reasignó VLAN, se crimpeó RJ45 Cat6 y se validó ping a gateway. Operativo.",
  },
  {
    key: "usuario",
    cat: "Usuario / Acceso",
    desc: "Usuario solicita restablecer credenciales de plataforma académica, cuenta bloqueada.",
    sol: "Se restableció contraseña en AD, desbloqueo y prueba de acceso OK.",
  },
  {
    key: "hardware",
    cat: "Hardware",
    desc: "Equipo no enciende, fuente sin voltaje, sin POST.",
    sol: "Se reemplazó fuente ATX 500W, test de encendido OK. Equipo entregado.",
  },
  {
    key: "software",
    cat: "Software",
    desc: "Solicitud instalación suite ofimática y actualización de antivirus.",
    sol: "Se instaló suite, se actualizó antivirus y se verificó licencia.",
  },
  {
    key: "impresora",
    cat: "Impresora",
    desc: "Impresora láser atasco papel bandeja 2, error 13.20.",
    sol: "Se retiró papel atascado, limpieza rodillos, impresión de prueba OK.",
  },
] as const;

const SUGERENCIAS_DESC = [
  "Sin conectividad en puerto — verificar patch panel",
  "Solicita restablecer IP estática",
];
const SUGERENCIAS_SOL = [
  "Se reemplazó cableado / conector RJ45",
  "Se reasignó VLAN y se validó ping",
];

interface BatchRow extends AtencionBatchItem {
  uid: string;
}

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

interface Props {
  jerarquia: JerarquiaSelection;
}

export default function AtencionTableV2({ jerarquia }: Props) {
  const { toast } = useToast();
  const [batch, setBatch] = useState<BatchRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [tecnicos, setTecnicos] = useState<Usuario[]>([]);

  const [form, setForm] = useState({
    medio: "Presencial",
    solicitante: "DOC",
    categoria: "Hardware",
    descripcion: "",
    solucion: "",
    observaciones: "",
    enlace: "",
    colaboradorId: 0,
    fueraDeTurno: false,
  });

  useEffect(() => {
    if (!API) return;
    fetch(`${API}/usuarios`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("auth_token") ?? ""}`,
      },
    })
      .then((r) => r.json())
      .then((d: Usuario[]) => setTecnicos(d))
      .catch(() => {});
  }, []);

  function patchForm(field: string, value: string | number | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  const hasJerarquia =
    jerarquia.padre &&
    jerarquia.area &&
    (!jerarquia.padre.grupos.length || jerarquia.grupo);

  const canAdd =
    hasJerarquia &&
    form.descripcion.trim() &&
    form.solucion.trim();

  function addToBatch() {
    if (!canAdd || !jerarquia.padre || !jerarquia.area) return;
    const row: BatchRow = {
      uid: uid(),
      grupoPadreId: jerarquia.padre.id,
      grupoPadre: jerarquia.padre.nombre,
      grupoId: jerarquia.grupo?.id ?? null,
      grupo: jerarquia.grupo?.nombre ?? null,
      areaId: jerarquia.area.id,
      area: jerarquia.area.nombre,
      medio: form.medio,
      usuarioSolicitante: form.solicitante,
      categoria: form.categoria,
      descripcion: form.descripcion.trim(),
      solucion: form.solucion.trim(),
      observaciones: form.observaciones.trim() || undefined,
      enlace: form.enlace.trim() || undefined,
      colaboradorId: form.colaboradorId || undefined,
      fueraDeTurno: form.fueraDeTurno,
    };
    setBatch((prev) => [...prev, row]);
    setForm((prev) => ({
      ...prev,
      descripcion: "",
      solucion: "",
      observaciones: "",
      enlace: "",
    }));
    toast(`Agregado al batch (${batch.length + 1})`);
  }

  function removeFromBatch(uid: string) {
    setBatch((prev) => prev.filter((r) => r.uid !== uid));
  }

  async function saveBatch() {
    if (!batch.length) return;
    setSaving(true);
    try {
      const { createAtenciones } = await import("@/lib/api");
      await createAtenciones(
        batch.map((b) => ({
          areaSolicitante: b.area,
          medioSolicitud: b.medio,
          usuarioSolicitante: b.usuarioSolicitante,
          categoria: b.categoria,
          descripcion: b.descripcion,
          solucion: b.solucion,
          observaciones: b.observaciones,
          enlaceApoyo: b.enlace,
          colaboradorId: b.colaboradorId,
          fechaRegistro: new Date().toISOString().slice(0, 10),
        }))
      );
      toast(`${batch.length} atención${batch.length !== 1 ? "es" : ""} guardada${batch.length !== 1 ? "s" : ""}`, "success");
      setBatch([]);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Error al guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  function applyPlantilla(key: string) {
    const p = PLANTILLAS.find((pl) => pl.key === key);
    if (!p) return;
    setForm((prev) => ({
      ...prev,
      categoria: p.cat,
      descripcion: p.desc,
      solucion: p.sol,
    }));
    toast(`Plantilla ${p.cat} aplicada`);
  }

  return (
    <div className="space-y-4">
      {/* Plantillas */}
      <div className="flex flex-wrap gap-2">
        {PLANTILLAS.map((p) => (
          <button
            key={p.key}
            onClick={() => applyPlantilla(p.key)}
            className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-[#00754A]/50 hover:text-[#00754A]"
          >
            {p.cat}
            <span className="text-slate-500">·</span>
            <span className="text-slate-500">{p.key}</span>
          </button>
        ))}
      </div>

      {/* Formulario */}
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[13px] font-bold text-slate-100">
            Datos de la atención
          </h3>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
              canAdd
                ? "bg-[#00754A]/15 text-[#00754A] ring-1 ring-[#00754A]/30"
                : "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30"
            }`}
          >
            {canAdd ? "Ruta válida" : "Ruta incompleta"}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Medio */}
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-slate-300">
              Medio <span className="text-red-400">*</span>
            </label>
            <select
              value={form.medio}
              onChange={(e) => patchForm("medio", e.target.value)}
              className="w-full rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 outline-none focus:border-[#00754A]"
            >
              {MEDIOS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Solicitante */}
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-slate-300">
              Solicitante <span className="text-red-400">*</span>
            </label>
            <select
              value={form.solicitante}
              onChange={(e) => patchForm("solicitante", e.target.value)}
              className="w-full rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 outline-none focus:border-[#00754A]"
            >
              {SOLICITANTES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Categoría pills */}
        <div className="mt-3">
          <label className="mb-1.5 block text-[12px] font-semibold text-slate-300">
            Categoría <span className="text-red-400">*</span>
          </label>
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIAS.map((c) => (
              <label
                key={c}
                className={`cursor-pointer rounded-full border-[1.5px] px-3 py-1.5 text-[13px] font-semibold transition ${
                  form.categoria === c
                    ? "border-[#00754A] bg-[#00754A] text-white"
                    : "border-white/15 hover:border-white/30"
                }`}
              >
                <input
                  type="radio"
                  name="cat"
                  value={c}
                  checked={form.categoria === c}
                  onChange={(e) => patchForm("categoria", e.target.value)}
                  className="sr-only"
                />
                {c}
              </label>
            ))}
          </div>
        </div>

        {/* Descripción */}
        <div className="mt-3">
          <label className="mb-1 block text-[12px] font-semibold text-slate-300">
            Descripción <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.descripcion}
            onChange={(e) => patchForm("descripcion", e.target.value)}
            placeholder="Describe la solicitud con detalle…"
            rows={3}
            className="w-full resize-vertical rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 placeholder-slate-500 outline-none focus:border-[#00754A]"
          />
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {SUGERENCIAS_DESC.map((s) => (
              <button
                key={s}
                onClick={() => patchForm("descripcion", s)}
                className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-400 transition hover:border-[#00754A]/50 hover:text-[#00754A]"
              >
                → {s}
              </button>
            ))}
          </div>
        </div>

        {/* Solución */}
        <div className="mt-3">
          <label className="mb-1 block text-[12px] font-semibold text-slate-300">
            Solución <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.solucion}
            onChange={(e) => patchForm("solucion", e.target.value)}
            placeholder="Detalla lo realizado…"
            rows={3}
            className="w-full resize-vertical rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 placeholder-slate-500 outline-none focus:border-[#00754A]"
          />
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {SUGERENCIAS_SOL.map((s) => (
              <button
                key={s}
                onClick={() => patchForm("solucion", s)}
                className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-400 transition hover:border-[#00754A]/50 hover:text-[#00754A]"
              >
                → {s}
              </button>
            ))}
          </div>
        </div>

        {/* Obs + Enlace */}
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-slate-300">
              Observaciones
            </label>
            <input
              type="text"
              value={form.observaciones}
              onChange={(e) => patchForm("observaciones", e.target.value)}
              placeholder="Ej. Requiere seguimiento mañana"
              className="w-full rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 placeholder-slate-500 outline-none focus:border-[#00754A]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-slate-300">
              Enlace (opcional)
            </label>
            <input
              type="text"
              value={form.enlace}
              onChange={(e) => patchForm("enlace", e.target.value)}
              placeholder="https://intranet…"
              className="w-full rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 placeholder-slate-500 outline-none focus:border-[#00754A]"
            />
          </div>
        </div>

        {/* Colaborador + Fuera turno */}
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-slate-300">
              Colaborador
            </label>
            <select
              value={form.colaboradorId}
              onChange={(e) =>
                patchForm("colaboradorId", Number(e.target.value))
              }
              className="w-full rounded border-[1.5px] border-white/15 bg-white/5 px-3 py-2.5 text-[13px] text-slate-100 outline-none focus:border-[#00754A]"
            >
              <option value={0}>— Sin colaborador —</option>
              {tecnicos.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.displayName}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex cursor-pointer items-center gap-2 text-[13px] font-semibold text-slate-300">
              <input
                type="checkbox"
                checked={form.fueraDeTurno}
                onChange={(e) => patchForm("fueraDeTurno", e.target.checked)}
                className="h-4 w-4 rounded border-white/20 bg-white/5 accent-[#00754A]"
              />
              Fuera de turno
              <span className="text-[12px] font-normal text-slate-500">
                se marca automático si corresponde
              </span>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <button
            onClick={addToBatch}
            disabled={!canAdd}
            className="inline-flex items-center gap-2 rounded-full bg-[#00754A] px-4 py-2 text-[13px] font-bold text-white transition hover:bg-[#00754A]/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ＋ Agregar al batch
          </button>
          <button
            onClick={() =>
              setForm({
                medio: "Presencial",
                solicitante: "DOC",
                categoria: "Hardware",
                descripcion: "",
                solucion: "",
                observaciones: "",
                enlace: "",
                colaboradorId: 0,
                fueraDeTurno: false,
              })
            }
            className="rounded-full border border-white/15 px-4 py-2 text-[13px] font-semibold text-slate-300 transition hover:border-white/30"
          >
            Limpiar
          </button>
          <span className="ml-auto text-[12px] text-slate-500">
            {canAdd
              ? "Listo para agregar al batch"
              : "Completa jerarquía + descripción/solución"}
          </span>
        </div>
      </div>

      {/* Batch table */}
      {batch.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5">
          <div className="flex items-center justify-between bg-[#1e3932] px-3.5 py-3">
            <strong className="text-[13px] text-white">
              Batch — registro múltiple
            </strong>
            <span className="text-[12px] text-white/60">
              {batch.length} en cola
            </span>
          </div>

          {/* Desktop table */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-white/5 bg-white/5">
                  {["#", "Ruta (Padre › Grupo › Área)", "Categoría", "Solicitante", ""].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-400"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {batch.map((b, i) => (
                  <tr
                    key={b.uid}
                    className="border-b border-white/5 transition hover:bg-white/5"
                  >
                    <td className="px-3 py-2.5 font-bold text-slate-200">
                      {i + 1}
                    </td>
                    <td className="px-3 py-2.5">
                      <strong className="text-slate-100">
                        {b.grupoPadre} › {b.grupo ?? "(Sin grupo)"} › {b.area}
                      </strong>
                      <br />
                      <span className="text-[11px] text-slate-500">
                        {b.categoria} · {b.medio}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-bold text-amber-400 ring-1 ring-amber-500/30">
                        {b.categoria.split(" ")[0]}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-300">
                      {b.usuarioSolicitante}
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        onClick={() => removeFromBatch(b.uid)}
                        className="flex h-6 w-6 items-center justify-center rounded-full border border-white/15 text-[11px] text-slate-400 transition hover:border-red-500/50 hover:text-red-400"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="space-y-2 p-3 md:hidden">
            {batch.map((b, i) => (
              <div
                key={b.uid}
                className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-bold text-slate-200">
                      #{i + 1}
                    </span>
                    <span className="truncate text-[12px] font-semibold text-slate-100">
                      {b.grupoPadre} › {b.grupo ?? "—"} › {b.area}
                    </span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-500">
                    {b.categoria} · {b.medio} · {b.usuarioSolicitante}
                  </div>
                </div>
                <button
                  onClick={() => removeFromBatch(b.uid)}
                  className="ml-2 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/15 text-[11px] text-slate-400 transition hover:border-red-500/50 hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-white/5 bg-white/5 px-3.5 py-3">
            <span className="text-[13px] text-slate-400">
              Se guardarán{" "}
              <strong className="text-slate-100">
                {batch.length} atención{batch.length !== 1 ? "es" : ""}
              </strong>{" "}
              con jerarquía (nombres)
            </span>
            <button
              onClick={saveBatch}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-full bg-[#00754A] px-5 py-2 text-[13px] font-bold text-white transition hover:bg-[#00754A]/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving ? (
                <>
                  <svg
                    className="h-4 w-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Guardando…
                </>
              ) : (
                "Guardar batch →"
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
