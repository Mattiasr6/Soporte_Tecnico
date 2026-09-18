"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import DashboardCardsV2 from "@/components/DashboardCardsV2";
import DashboardStatsV2 from "@/components/DashboardStatsV2";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function HomePage() {
  const { user } = useAuth();
  const router = useRouter();

  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) router.replace("/soporte");
  }, [user, canAccess, router]);

  if (!user || !canAccess) return null;

  return (
    <main className="mx-auto max-w-[1440px] px-4 py-4 lg:px-10 lg:py-6">
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-lg font-bold text-[#006241]">Dashboard</h1>
        <span className="rounded-full bg-[#00754A] px-3 py-1 text-[11px] font-bold text-white">V2</span>
      </div>

      <ErrorBoundary fallback={<p className="text-sm text-red-400">Error al cargar KPIs jerárquicos</p>}>
        <section><DashboardCardsV2 /></section>
      </ErrorBoundary>

      <ErrorBoundary fallback={<p className="text-sm text-red-400">Error al cargar estadísticas</p>}>
        <section className="mt-4"><DashboardStatsV2 /></section>
      </ErrorBoundary>
    </main>
  );
}
