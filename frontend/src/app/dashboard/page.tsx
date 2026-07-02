"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import DashboardCards from "@/components/DashboardCards";
import DashboardStats from "@/components/DashboardStats";
import CompareTecnicos from "@/components/CompareTecnicos";

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();

  const canAccess = user?.role === "Jefe" || user?.canViewDashboard;

  useEffect(() => {
    if (user && !canAccess) {
      router.replace("/soporte");
    }
  }, [user, canAccess, router]);

  if (!user || !canAccess) {
    return null;
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-3 py-4 lg:px-6 lg:py-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 lg:text-2xl">Dashboard</h1>
        <p className="mt-0.5 text-xs text-slate-400 lg:text-sm">
          Estado en tiempo real del equipo de soporte
        </p>
      </div>

      <section>
        <DashboardCards />
      </section>

      <section>
        <DashboardStats />
      </section>

      <section>
        <CompareTecnicos />
      </section>
    </main>
  );
}
