"use client";

import { useState, useRef } from "react";
import { importCsv } from "@/lib/api";
import { useToast } from "./Toast";

export default function CsvDropzone() {
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const processFile = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      toast("El archivo debe ser .csv", "error");
      return;
    }
    setImporting(true);
    try {
      const res = await importCsv(file);
      toast(`Se importaron ${res.registrosInsertados} registros.`, "success");
      if (res.errores?.length) {
        toast(`${res.errores.length} líneas con errores.`, "info");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Error al importar", "error");
    } finally {
      setImporting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => fileRef.current?.click()}
      className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all ${
        dragging
          ? "border-amber-500 bg-amber-500/5 shadow-lg shadow-amber-500/10"
          : "border-slate-700 bg-slate-800/30 hover:border-slate-500"
      }`}
    >
      <input ref={fileRef} type="file" accept=".csv" onChange={handleChange} className="hidden" />

      {importing ? (
        <div className="flex flex-col items-center gap-2">
          <svg className="h-8 w-8 animate-spin text-amber-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-sm text-slate-400">Importando...</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <svg className={`h-8 w-8 transition-colors ${dragging ? "text-amber-400" : "text-slate-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          <p className="text-sm text-slate-400">
            <span className="font-medium text-slate-300">{dragging ? "Suelta el archivo" : "Arrastra tu CSV aquí"}</span>
            {" o haz clic para seleccionar"}
          </p>
          <p className="text-xs text-slate-600">Solo archivos .csv</p>
        </div>
      )}
    </div>
  );
}
