import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import MsalProviderWrapper from "@/components/MsalProviderWrapper";
import MockAuthProvider from "@/components/MockAuthProvider";

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
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";

  return (
    <html lang="es" className={`${dmSans.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-slate-950 font-body text-slate-100 antialiased">
        {isMock ? (
          <MockAuthProvider>{children}</MockAuthProvider>
        ) : (
          <MsalProviderWrapper>{children}</MsalProviderWrapper>
        )}
      </body>
    </html>
  );
}
