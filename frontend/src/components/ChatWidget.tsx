"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSignalR } from "@/lib/SignalRProvider";
import { useAuth } from "./AuthProvider";

export default function ChatWidget() {
  const { connected, messages, sendMessage } = useSignalR();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [texto, setTexto] = useState("");
  const [noLeidos, setNoLeidos] = useState(0);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; posX: number; posY: number }>({ startX: 0, startY: 0, posX: 0, posY: 0 });
  const bottomRef = useRef<HTMLDivElement>(null);
  const msgsRef = useRef(messages.length);

  useEffect(() => {
    if (open && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, [open]);

  useEffect(() => {
    if (!open && messages.length > msgsRef.current) {
      setNoLeidos((n) => n + messages.length - msgsRef.current);
    }
    msgsRef.current = messages.length;
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const panelRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = panelRef.current?.getBoundingClientRect();
    if (rect) {
      dragRef.current.startX = e.clientX;
      dragRef.current.startY = e.clientY;
      dragRef.current.posX = pos.x || rect.left;
      dragRef.current.posY = pos.y || rect.top;
    }
    setDragging(true);
  }, [pos]);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPos({ x: dragRef.current.posX + dx, y: dragRef.current.posY + dy });
    };
    const onUp = () => setDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, [dragging]);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!texto.trim()) return;
    await sendMessage(texto.trim());
    setTexto("");
  };

  return (
    <>
      {/* Boton flotante — se reposiciona si el chat se movio */}
      <button
        onClick={() => { setOpen(!open); setNoLeidos(0); }}
        className="fixed bottom-4 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-amber-500 to-amber-600 text-slate-950 shadow-2xl transition hover:scale-105"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        {noLeidos > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {noLeidos > 9 ? "9+" : noLeidos}
          </span>
        )}
        {!connected && (
          <span className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-red-500 ring-2 ring-slate-900" />
        )}
      </button>

      {/* Panel de chat — arrastrable por el header */}
      {open && (
        <div
          className="fixed z-50 flex w-80 flex-col rounded-2xl border border-slate-700/50 bg-slate-900 shadow-2xl"
          style={pos.x || pos.y ? { left: pos.x, top: pos.y } : { right: 16, bottom: 80 }}
        >
          {/* Header arrastrable */}
          <div
            onMouseDown={onMouseDown}
            className={`flex cursor-grab items-center justify-between border-b border-slate-700/50 px-4 py-3 select-none ${dragging ? "cursor-grabbing" : ""}`}
          >
            <div className="flex items-center gap-2">
              <span className={`inline-block h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
              <span className="text-sm font-semibold text-slate-200">Chat del equipo</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-xs text-slate-500 hover:text-slate-300">✕</button>
          </div>

          <div className="flex h-72 flex-col gap-2 overflow-y-auto p-3">
            {messages.length === 0 && (
              <p className="flex-1 pt-10 text-center text-xs text-slate-500">Sin mensajes aún</p>
            )}
            {messages.map((m, i) => {
              const esYo = m.nombre === user?.displayName;
              return (
                <div key={i} className={`flex flex-col ${esYo ? "items-end" : "items-start"}`}>
                  <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs ${
                    esYo
                      ? "bg-amber-500/20 text-amber-200"
                      : m.role === "Jefe"
                        ? "bg-sky-500/20 text-sky-200"
                        : "bg-slate-700/60 text-slate-200"
                  }`}>
                    {!esYo && (
                      <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider opacity-70">{m.nombre}</p>
                    )}
                    <p>{m.message}</p>
                  </div>
                  <span className="mt-0.5 text-[9px] text-slate-600">{m.timestamp}</span>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={enviar} className="flex items-center gap-2 border-t border-slate-700/50 p-3">
            <input
              type="text" value={texto} onChange={(e) => setTexto(e.target.value)}
              placeholder="Escribe un mensaje..." maxLength={500}
              className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 transition focus:border-amber-500/50 focus:outline-none"
            />
            <button type="submit" disabled={!texto.trim()}
              className="rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-slate-900 transition hover:bg-amber-400 disabled:opacity-40"
            >→</button>
          </form>
        </div>
      )}
    </>
  );
}
