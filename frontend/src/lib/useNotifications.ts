"use client";

import { useEffect } from "react";
import { useSignalR } from "./SignalRProvider";

const estadoEmoji: Record<string, string> = {
  ocupado: "🔴",
  disponible: "🟢",
  ausente: "⚫",
  extraturno: "🟠",
};

export default function useNotifications() {
  const { lastStatus, messages } = useSignalR();

  useEffect(() => {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (!lastStatus || !("Notification" in window)) return;
    if (Notification.permission !== "granted") return;

    const emoji = estadoEmoji[lastStatus.estado] ?? "🔵";
    const estadoTexto = lastStatus.estado === "ocupado"
      ? lastStatus.motivo === "colaborando"
        ? `colaborando${lastStatus.colaboradorNombre ? ` con ${lastStatus.colaboradorNombre}` : ""}`
        : "atendiendo"
      : lastStatus.estado === "extraturno"
        ? "en horario extendido (fuera de turno)"
        : lastStatus.estado;

    new Notification(`${emoji} ${lastStatus.nombre}`, {
      body: `${lastStatus.nombre} está ${estadoTexto}`,
      icon: "/favicon.ico",
      silent: true,
    });
  }, [lastStatus]);

  useEffect(() => {
    if (messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (!("Notification" in window)) return;
    if (Notification.permission !== "granted") return;

    new Notification(`💬 ${last.nombre}`, {
      body: last.message.slice(0, 100),
      icon: "/favicon.ico",
      silent: true,
    });
  }, [messages.length]);
}
