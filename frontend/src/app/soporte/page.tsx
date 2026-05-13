import ToggleButton from "@/components/ToggleButton";
import AtencionTable from "@/components/AtencionTable";

export default function SoportePage() {
  return (
    <main className="mx-auto max-w-6xl space-y-10 p-6">
      <section className="flex flex-col items-center pt-4">
        <h1 className="text-2xl font-bold text-slate-100">Panel del Técnico</h1>
        <p className="mt-1 text-sm text-slate-400">
          Cambia tu estado y registra las atenciones realizadas
        </p>
        <div className="mt-6">
          <ToggleButton />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-100">
          Registro de Atenciones
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Ingresa todas las atenciones que realizaste. Usa el botón{" "}
          <strong className="text-slate-300">+</strong> para agregar
          observaciones si la tarea fue extensa o compleja.
        </p>
        <div className="mt-4">
          <AtencionTable />
        </div>
      </section>
    </main>
  );
}
