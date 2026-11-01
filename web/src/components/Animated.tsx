import { useEffect, useRef, useState, type ReactNode } from "react";

/** Visitors who ask their system for less motion get static numbers and charts. */
export const REDUCED_MOTION = typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Renders its children once the box scrolls into view, so chart animations play when seen. */
export function InView({ children, className = "h-full w-full" }: { children: () => ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(REDUCED_MOTION);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (!("IntersectionObserver" in window)) { setSeen(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.25 });
    io.observe(el);
    return () => io.disconnect();
  }, [seen]);
  return <div ref={ref} className={className}>{seen ? children() : null}</div>;
}

/** Counts from 0 up to `value` when first shown. */
export function CountUp({ value, decimals = 0, suffix = "", grouping = false, ms = 1200 }:
  { value: number; decimals?: number; suffix?: string; grouping?: boolean; ms?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(REDUCED_MOTION ? value : 0);
  useEffect(() => {
    if (REDUCED_MOTION) { setShown(value); return; }
    const el = ref.current;
    let raf = 0;
    const run = () => {
      const t0 = performance.now();
      const tick = (t: number) => {
        const k = Math.min(1, (t - t0) / ms);
        setShown(value * (1 - Math.pow(1 - k, 3)));
        if (k < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    };
    if (!el || !("IntersectionObserver" in window)) { setShown(value); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { run(); io.disconnect(); } }, { threshold: 0.4 });
    io.observe(el);
    return () => { io.disconnect(); cancelAnimationFrame(raf); };
  }, [value, ms]);
  const text = grouping ? Math.round(shown).toLocaleString() : shown.toFixed(decimals);
  return <span ref={ref} className="tabular-nums">{text}{suffix}</span>;
}
