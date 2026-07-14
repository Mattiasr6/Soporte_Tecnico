"use client";

import { createContext, useContext, useEffect, useState, useRef, ReactNode } from "react";
import { useAuth } from "@/components/AuthProvider";
import * as signalR from "@microsoft/signalr";

interface ChatMessage {
  nombre: string;
  role: string;
  message: string;
  timestamp: string;
}

export interface StatusEvent {
  usuarioId: number;
  nombre: string;
  estado: string;
  motivo: string | null;
  colaboradorNombre: string | null;
  timestamp: string;
}

interface SignalRContextValue {
  connected: boolean;
  messages: ChatMessage[];
  sendMessage: (msg: string) => Promise<void>;
  lastStatus: StatusEvent | null;
}

const SignalRCtx = createContext<SignalRContextValue>(null!);
export const useSignalR = () => useContext(SignalRCtx);

export function SignalRProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastStatus, setLastStatus] = useState<StatusEvent | null>(null);
  const connRef = useRef<signalR.HubConnection | null>(null);

  useEffect(() => {
    if (!token || !user) return;

    const hostname = window.location.hostname;
    const conn = new signalR.HubConnectionBuilder()
      .withUrl(`http://${hostname}:5000/hub`, {
        accessTokenFactory: () => token,
      })
      .withAutomaticReconnect()
      .build();

    conn.on("ReceiveMessage", (msg: ChatMessage) => {
      setMessages((prev) => [...prev.slice(-49), msg]);
    });

    conn.on("StatusChanged", (ev: StatusEvent) => {
      setLastStatus(ev);
    });

    conn.start().then(() => setConnected(true)).catch(() => {});

    connRef.current = conn;

    return () => { conn.stop(); connRef.current = null; };
  }, [token, user]);

  const sendMessage = async (msg: string) => {
    if (connRef.current?.state === signalR.HubConnectionState.Connected) {
      await connRef.current.invoke("SendMessage", msg);
    }
  };

  return (
    <SignalRCtx.Provider value={{ connected, messages, sendMessage, lastStatus }}>
      {children}
    </SignalRCtx.Provider>
  );
}
