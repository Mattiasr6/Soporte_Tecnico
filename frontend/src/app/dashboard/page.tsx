import DashboardCards from "@/components/DashboardCards";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-400">
        Estado en tiempo real del equipo de soporte
      </p>
      <div className="mt-6">
        <DashboardCards />
      </div>
    </main>
  );
}
