"use client";

import { useEffect, useRef } from "react";
import { useSignalR } from "./SignalRProvider";

const estadoEmoji: Record<string, string> = {
  ocupado: "🔴",
  disponible: "🟢",
  ausente: "⚫",
  extraturno: "🟠",
};

export default function useNotifications() {
  const { lastStatus, messages } = useSignalR();
  const lastKnownLen = useRef(messages.length);

  // Pedir permiso al cargar
  useEffect(() => {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Notificación de cambio de estado
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

  // Notificación de nuevo mensaje — solo si hay mensajes NUEVOS
  useEffect(() => {
    if (messages.length === 0) return;
    if (!("Notification" in window)) return;
    if (Notification.permission !== "granted") return;

    // Solo notificar si aumentó la cantidad de mensajes
    if (messages.length <= lastKnownLen.current) return;

    const last = messages[messages.length - 1];
    new Notification(`💬 ${last.nombre}`, {
      body: last.message.slice(0, 100),
      icon: "/favicon.ico",
      silent: true,
    });

    lastKnownLen.current = messages.length;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length]);
}
