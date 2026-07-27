"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { useSignalR } from "@/lib/SignalRProvider";

export default function AnnouncementModal({ onClose }: { onClose: () => void }) {
  const { token } = useAuth();
  const { announcement } = useSignalR();
  const [text, setText] = useState(announcement ?? "");
  const [sending, setSending] = useState(false);
  const apiUrl = typeof window !== "undefined" ? `http://${window.location.hostname}:5000/api/announcements` : "";

  const publish = async () => {
    if (!token) return;
    setSending(true);
    try {
      await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: text.trim() || null }),
      });
    } catch { /* ignore */ }
    setSending(false);
    onClose();
  };

  const clear = async () => {
    if (!token) return;
    setSending(true);
    try {
      await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: null }),
      });
    } catch { /* ignore */ }
    setSending(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="mx-4 w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-bold text-slate-100">Anuncio General</h2>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Escribe el anuncio para todos los técnicos..."
          rows={4}
          className="mb-4 w-full resize-none rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
        />

        <div className="flex gap-3">
          <button
            onClick={publish}
            disabled={sending || !text.trim()}
            className="flex-1 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:from-amber-400 hover:to-amber-500 disabled:opacity-50"
          >
            {sending ? "Publicando..." : "Publicar"}
          </button>
          {announcement && (
            <button
              onClick={clear}
              disabled={sending}
              className="rounded-xl bg-red-600/20 px-4 py-2.5 text-sm font-medium text-red-400 transition hover:bg-red-600/30"
            >
              Quitar
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-slate-700"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
