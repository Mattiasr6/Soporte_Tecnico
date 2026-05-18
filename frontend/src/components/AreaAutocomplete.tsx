"use client";

import { useState, useRef, useEffect } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  areas: string[];
  placeholder?: string;
}

export default function AreaAutocomplete({ value, onChange, areas, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState(value);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = areas.filter((a) =>
    a.toLowerCase().includes(filter.toLowerCase())
  );

  useEffect(() => {
    setFilter(value);
  }, [value]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <input
        type="text"
        value={filter}
        onChange={(e) => {
          setFilter(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder || "Buscar área..."}
        className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
      />
      {open && filtered.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-600 bg-slate-900 shadow-xl">
          {filtered.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => {
                onChange(a);
                setFilter(a);
                setOpen(false);
              }}
              className="w-full px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-amber-600/20 hover:text-amber-400"
            >
              {a}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
