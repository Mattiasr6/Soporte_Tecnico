"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/Toast";

function parseHora(h: string): number {
  const [hh, mm] = h.split(":").map(Number);
  return hh * 60 + mm;
}

export default function useScheduleReminder() {
  const { user, token } = useAuth();
  const { toast } = useToast();
  const [horario, setHorario] = useState<{ label: string; horaFin1: string; horaFin2?: string } | null>(null);

  useEffect(() => {
    if (!token || !user) return;
    const now = new Date();
    const hostname = window.location.hostname;

    fetch(`http://${hostname}:5000/api/horarios?mes=${now.getMonth() + 1}&anio=${now.getFullYear()}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((r) => r.json())
      .then((h) => {
        const miH = (h as any[]).find((x: any) => x.usuarioId === user.id);
        if (miH) setHorario(miH);
      })
      .catch(() => {});
  }, [token, user]);

  useEffect(() => {
    if (!horario || typeof window === "undefined") return;

    const avisados = new Set<string>();

    const check = () => {
      const ahora = new Date();
      const minutos = ahora.getHours() * 60 + ahora.getMinutes();
      const notificar = (bloque: string, horaFin: string) => {
        const fin = parseHora(horaFin);
        const diff = fin - minutos;
        if (diff > 0 && diff <= 30 && !avisados.has(bloque)) {
          avisados.add(bloque);
          toast("⏰ Falta poco para salir — recuerda anotar tus atenciones", "info");

          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("⏰ Fin del turno", {
              body: `Falta poco para salir (${horaFin}). Recuerda registrar tus atenciones.`,
              silent: true,
            });
          }
        }
      };

      if (horario.horaFin1) notificar("bloque1", horario.horaFin1);
      if (horario.horaFin2) notificar("bloque2", horario.horaFin2);
    };

    check();
    const interval = setInterval(check, 60000);
    return () => clearInterval(interval);
  }, [horario, toast]);
}
