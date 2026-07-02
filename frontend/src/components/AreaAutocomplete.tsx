"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

interface Props {
  value: string;
  onChange: (value: string) => void;
  areas: string[];
  placeholder?: string;
}

export default function AreaAutocomplete({ value, onChange, areas, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });

  const filtered = areas.filter((a) =>
    a.toLowerCase().includes(filter.toLowerCase())
  );

  useEffect(() => {
    setFilter(value);
  }, [value]);

  const updateCoords = () => {
    const rect = inputRef.current?.getBoundingClientRect();
    if (rect) {
      setCoords({ top: rect.bottom + 4, left: rect.left, width: rect.width });
    }
  };

  // Mousedown global: cierra si click NO está en input NI en portal
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const inInput = inputRef.current?.contains(target);
      const inList = listRef.current?.contains(target);
      if (!inInput && !inList) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Scroll global: cierra SOLO si scroll NO es dentro del portal
  useEffect(() => {
    if (!open) return;
    const handler = (e: Event) => {
      const target = e.target as Node;
      if (listRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("scroll", handler, { capture: true });
    return () => document.removeEventListener("scroll", handler, { capture: true });
  }, [open]);

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={filter}
        onChange={(e) => {
          setFilter(e.target.value);
          onChange(e.target.value);
          updateCoords();
          setOpen(true);
        }}
        onFocus={() => {
          updateCoords();
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        placeholder={placeholder || "Buscar área..."}
        className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
      />
      {open && filtered.length > 0 && coords.top > 0 &&
        createPortal(
          <div
            ref={listRef}
            style={{
              position: "fixed",
              top: coords.top,
              left: coords.left,
              width: coords.width,
            }}
            className="z-[9999] max-h-60 overflow-y-auto rounded-lg border border-slate-600 bg-slate-900 shadow-xl"
          >
            {filtered.map((a) => (
              <button
                key={a}
                type="button"
                onMouseDown={(e) => e.stopPropagation()}
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
          </div>,
          document.body
        )}
    </div>
  );
}
