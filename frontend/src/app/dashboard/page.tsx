"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import DashboardCardsV2 from "@/components/DashboardCardsV2";
import DashboardStatsV2 from "@/components/DashboardStatsV2";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();

  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) router.replace("/soporte");
  }, [user, canAccess, router]);

  if (!user || !canAccess) return null;

  return (
    <main className="mx-auto max-w-[1440px] px-4 py-4 lg:px-10 lg:py-6">
      <h1 className="mb-4 text-lg font-bold text-[#006241]">Dashboard</h1>

      <ErrorBoundary fallback={<p className="text-sm text-red-400">Error al cargar KPIs jerárquicos</p>}>
        <section><DashboardCardsV2 /></section>
      </ErrorBoundary>

      <ErrorBoundary fallback={<p className="text-sm text-red-400">Error al cargar estadísticas</p>}>
        <section className="mt-4"><DashboardStatsV2 /></section>
      </ErrorBoundary>
    </main>
  );
}
