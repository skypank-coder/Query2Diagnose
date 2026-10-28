import type { ReactNode } from "react";

export function Bar({ value, max, color = "bg-accent-500", label }: { value: number; max: number; color?: string; label?: ReactNode }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      {label && <div className="mb-1 flex justify-between text-xs">{label}</div>}
      <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 font-serif text-3xl font-semibold text-slate-900 dark:text-white">{value}</div>
      {hint && <div className="mt-1 text-xs muted">{hint}</div>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center py-14 text-center">
      <div className="text-4xl">∅</div>
      <h3 className="mt-3 font-serif text-xl font-semibold">{title}</h3>
      <div className="mt-2 max-w-lg text-sm muted">{children}</div>
    </div>
  );
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return <div className="card animate-pulse py-10 text-center text-sm muted">{what}…</div>;
}

export function Section({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="h-section">{title}</h2>
      {subtitle && <p className="mt-1 text-sm muted">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}
