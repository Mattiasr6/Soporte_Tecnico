"use client";

import { useEffect, useState } from "react";
import { getAtenciones, getUsuarios, updateAtencion, deleteAtencion, getAreas } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { useToast } from "./Toast";
import type { AtencionItem, Usuario } from "@/types";

const CATEGORIAS = [
  "Audio/Video", "Cuentas/Accesos", "Hardware", "Impresión",
  "Otros", "Redes/Conectividad", "Sistemas académicos", "Software",
];
const MEDIOS = ["Interno", "Presencial", "WhatsApp", "E-ticket"];
const USUARIOS_SOL = ["ADM", "BEC", "DOC"];

export default function HistorialModal({
  onClose,
  initialUsuarioId,
}: {
  onClose: () => void;
  initialUsuarioId?: number;
}) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [atenciones, setAtenciones] = useState<AtencionItem[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [filtroUsuario, setFiltroUsuario] = useState<number | "">(initialUsuarioId ?? "");
  const [loading, setLoading] = useState(true);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [eliminandoId, setEliminandoId] = useState<number | null>(null);
  const [busqueda, setBusqueda] = useState("");

  const isJefe = user?.role === "Jefe";

  useEffect(() => {
    if (isJefe) {
      Promise.all([getUsuarios(), getAreas()])
        .then(([u, a]) => { setUsuarios(u); setAreas(a); })
        .catch(() => {});
    }
  }, [isJefe]);

  useEffect(() => {
    setLoading(true);
    getAtenciones(filtroUsuario || undefined)
      .then(setAtenciones)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filtroUsuario]);

  const puedeModificar = (a: AtencionItem) =>
    user?.role === "Jefe" || a.usuarioId === user?.id;

  const iniciarEdicion = (a: AtencionItem) => {
    setEditandoId(a.id);
    setEditForm({
      areaSolicitante: a.areaSolicitante,
      medioSolicitud: a.medioSolicitud,
      usuarioSolicitante: a.usuarioSolicitante,
      categoria: a.categoria,
      descripcion: a.descripcion,
      solucion: a.solucion,
      observaciones: a.observaciones ?? "",
      enlaceApoyo: a.enlaceApoyo ?? "",
    });
  };

  const guardarEdicion = async (id: number) => {
    try {
      await updateAtencion(id, editForm);
      toast("Atención actualizada", "success");
      setEditandoId(null);
      const data = await getAtenciones(filtroUsuario || undefined);
      setAtenciones(data);
    } catch { toast("Error al actualizar", "error"); }
  };

  const cancelarEdicion = () => {
    setEditandoId(null);
    setEditForm({});
  };

  const confirmarEliminar = async (id: number) => {
    try {
      await deleteAtencion(id);
      toast("Atención eliminada", "success");
      setEliminandoId(null);
      setAtenciones((prev) => prev.filter((a) => a.id !== id));
    } catch { toast("Error al eliminar", "error"); }
  };

  const q = busqueda.toLowerCase();
  const filtradas = q
    ? atenciones.filter((a) =>
        [a.areaSolicitante, a.medioSolicitud, a.categoria, a.descripcion, a.solucion, a.usuarioNombre]
          .some((v) => v?.toLowerCase().includes(q))
      )
    : atenciones;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-10 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-6xl rounded-2xl border border-slate-700/50 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-700/50 px-6 py-4">
          <h2 className="text-lg font-bold text-slate-100">Historial de Atenciones</h2>
          <div className="flex items-center gap-3">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input type="text" value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar..." className="w-48 rounded-lg border border-slate-600 bg-slate-800 py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none" />
            </div>
            {isJefe && (
              <select value={filtroUsuario} onChange={(e) => setFiltroUsuario(e.target.value ? Number(e.target.value) : "")}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50">
                <option value="">Todos</option>
                {usuarios.map((u) => (<option key={u.id} value={u.id}>{u.displayName}</option>))}
              </select>
            )}
            <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition hover:bg-slate-800 hover:text-white">Cerrar</button>
          </div>
        </div>

        <div className="max-h-[70vh] overflow-auto p-6">
          {loading ? (
            <div className="flex justify-center py-12 text-slate-500">
              <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="ml-2 text-sm">Cargando...</span>
            </div>
          ) : filtradas.length === 0 ? (
            <p className="py-12 text-center text-sm text-slate-500">No hay atenciones registradas.</p>
          ) : (
            <>
              <p className="mb-2 text-xs text-slate-500">{filtradas.length} resultado{filtradas.length !== 1 ? "s" : ""}</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700 text-slate-400">
                      <th className="whitespace-nowrap p-2 text-left font-semibold">Fecha</th>
                      {isJefe && <th className="whitespace-nowrap p-2 text-left font-semibold">Técnico</th>}
                      <th className="whitespace-nowrap p-2 text-left font-semibold">Área</th>
                      <th className="whitespace-nowrap p-2 text-left font-semibold">Medio</th>
                      <th className="whitespace-nowrap p-2 text-left font-semibold">Usuario</th>
                      <th className="whitespace-nowrap p-2 text-left font-semibold">Categoría</th>
                      <th className="p-2 text-left font-semibold">Descripción</th>
                      <th className="p-2 text-left font-semibold">Solución</th>
                      <th className="p-2 text-center font-semibold">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtradas.map((a) => {
                      const editando = editandoId === a.id;
                      return (
                        <tr key={a.id} className="border-b border-slate-800 text-slate-300 transition-colors hover:bg-slate-800/40">
                          <td className="whitespace-nowrap p-2 text-xs">{a.fechaRegistro}</td>
                          {isJefe && <td className="whitespace-nowrap p-2 text-xs text-slate-400">{a.usuarioNombre}</td>}
                          {editando ? (
                            <>
                              <td className="p-1"><input value={editForm.areaSolicitante} onChange={(e) => setEditForm((f) => ({ ...f, areaSolicitante: e.target.value }))} list="areas-list" className="w-28 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100" /><datalist id="areas-list">{areas.map((ar) => <option key={ar} value={ar} />)}</datalist></td>
                              <td className="p-1"><select value={editForm.medioSolicitud} onChange={(e) => setEditForm((f) => ({ ...f, medioSolicitud: e.target.value }))} className="w-24 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100">{MEDIOS.map((m) => <option key={m} value={m}>{m}</option>)}</select></td>
                              <td className="p-1"><select value={editForm.usuarioSolicitante} onChange={(e) => setEditForm((f) => ({ ...f, usuarioSolicitante: e.target.value }))} className="w-16 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100">{USUARIOS_SOL.map((u) => <option key={u} value={u}>{u}</option>)}</select></td>
                              <td className="p-1"><select value={editForm.categoria} onChange={(e) => setEditForm((f) => ({ ...f, categoria: e.target.value }))} className="w-28 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100">{CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}</select></td>
                              <td className="p-1"><input value={editForm.descripcion} onChange={(e) => setEditForm((f) => ({ ...f, descripcion: e.target.value }))} className="w-36 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100" /></td>
                              <td className="p-1"><input value={editForm.solucion} onChange={(e) => setEditForm((f) => ({ ...f, solucion: e.target.value }))} className="w-36 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100" /></td>
                              <td className="whitespace-nowrap p-1"><div className="flex items-center gap-1"><button onClick={() => guardarEdicion(a.id)} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white transition hover:bg-emerald-500">Guardar</button><button onClick={cancelarEdicion} className="rounded bg-slate-600 px-2 py-1 text-xs text-white transition hover:bg-slate-500">Cancelar</button></div></td>
                            </>
                          ) : (
                            <>
                              <td className="whitespace-nowrap p-2 text-xs">{a.areaSolicitante}</td>
                              <td className="whitespace-nowrap p-2 text-xs">{a.medioSolicitud}</td>
                              <td className="whitespace-nowrap p-2 text-xs">{a.usuarioSolicitante}</td>
                              <td className="whitespace-nowrap p-2 text-xs">{a.categoria}</td>
                              <td className="max-w-[200px] truncate p-2 text-xs" title={a.descripcion}>{a.descripcion}</td>
                              <td className="max-w-[200px] truncate p-2 text-xs" title={a.solucion}>{a.solucion}</td>
                              <td className="whitespace-nowrap p-1">
                                {puedeModificar(a) && (
                                  <div className="flex items-center justify-center gap-1">
                                    <button onClick={() => iniciarEdicion(a)} className="flex h-7 w-7 items-center justify-center rounded text-slate-400 transition hover:bg-amber-600 hover:text-white" title="Editar">
                                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                                    </button>
                                    {eliminandoId === a.id ? (
                                      <div className="flex items-center gap-1">
                                        <button onClick={() => confirmarEliminar(a.id)} className="rounded bg-red-600 px-2 py-1 text-xs text-white transition hover:bg-red-500">Eliminar</button>
                                        <button onClick={() => setEliminandoId(null)} className="rounded bg-slate-600 px-2 py-1 text-xs text-white transition hover:bg-slate-500">Cancelar</button>
                                      </div>
                                    ) : (
                                      <button onClick={() => setEliminandoId(a.id)} className="flex h-7 w-7 items-center justify-center rounded text-slate-400 transition hover:bg-red-600 hover:text-white" title="Eliminar">
                                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                      </button>
                                    )}
                                  </div>
                                )}
                              </td>
                            </>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <div className="border-t border-slate-700/50 px-6 py-3 text-right text-xs text-slate-500">
          {filtradas.length} registro{filtradas.length !== 1 ? "s" : ""}
        </div>
      </div>
    </div>
  );
}
