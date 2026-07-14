import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import { ToastProvider } from "@/components/Toast";
import { SignalRProvider } from "@/lib/SignalRProvider";
import Navbar from "@/components/Navbar";
import ChatWidget from "@/components/ChatWidget";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Soporte Técnico",
  description: "Sistema de registro de atenciones técnicas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`${dmSans.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-slate-950 font-body text-slate-100 antialiased">
        <AuthProvider>
          <ToastProvider>
            <SignalRProvider>
              <div className="lg:flex">
                <Navbar />
                <main className="flex-1 pt-14 lg:pt-0">{children}</main>
              </div>
              <ChatWidget />
            </SignalRProvider>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
