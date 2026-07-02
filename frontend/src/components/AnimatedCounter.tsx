"use client";

import { useEffect, useState, useRef } from "react";

export default function AnimatedCounter({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 },
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    const duration = 600;
    const steps = 20;
    const step = Math.max(1, Math.floor(value / steps));
    let current = 0;
    const interval = setInterval(() => {
      current = Math.min(current + step, value);
      setDisplay(current);
      if (current >= value) clearInterval(interval);
    }, duration / steps);
    return () => clearInterval(interval);
  }, [visible, value]);

  return (
    <span ref={ref} className="animate-count inline-block">
      {display.toLocaleString()}{suffix}
    </span>
  );
}
