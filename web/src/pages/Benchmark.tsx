import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, CONDITION_LABEL, pretty, type Stats } from "../api";
import { Empty, Loading, Section, Stat } from "../components/ui";

export default function Benchmark() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.stats().then(setStats).catch(() => setError(true)); }, []);
  if (error) return <Empty title="Benchmark statistics unavailable">Start the API (<code>make api</code>) to load them.</Empty>;
  if (!stats) return <Loading what="Loading benchmark" />;
  const prov = Object.entries(stats.provenance);
  const total = prov.reduce((a, [, n]) => a + n, 0);
  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold text-slate-900 dark:text-white">Benchmark</h1>
      <p className="mt-2 max-w-3xl muted">
        Domestic-refrigerator troubleshooting cases built from 47 scenarios, each tied to a quoted iFixit or ENERGY STAR passage.
        Every underlying case appears under seven input conditions; all variants of a case stay in one split.
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Underlying cases" value={stats.n_cases} hint={`${stats.faults.length} fault categories`} />
        <Stat label="Variants" value={stats.n_variants} hint={`+ ${stats.n_stress} Kannada+Hindi stress`} />
        <Stat label="Split" value={`${stats.splits.train}/${stats.splits.val}/${stats.splits.test}`} hint="train / val / test (case level)" />
        <Stat label="Cohen's κ" value={stats.kappa ? Object.values(stats.kappa)[0].kappa.toFixed(2) : "—"} hint={stats.kappa ? "annotator agreement" : "not run yet"} />
      </div>

      <Section title="One case under every condition" subtitle={`Case ${stats.example.case_id} · hidden fault: ${pretty(stats.example.fault)} · gold action: ${pretty(stats.example.gold_action)}`}>
        <div className="grid gap-3 md:grid-cols-2">
          {stats.example.variants.map((v) => (
            <div key={v.condition} className="card">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold uppercase tracking-wide text-accent-700 dark:text-accent-400">{CONDITION_LABEL[v.condition]}</span>
                <span className="muted">{v.lang_pair}</span>
              </div>
              <p className="mt-2 font-mono text-sm">{v.text}</p>
              <p className="mt-2 text-xs muted">mentions: {v.mentioned.filter((a) => a !== "device").map(pretty).join(", ")}</p>
            </div>
          ))}
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Fault distribution" subtitle="Red: unsafe faults (gold action is always REFER)">
          <div className="card h-96">
            <ResponsiveContainer>
              <BarChart data={stats.faults} layout="vertical" margin={{ left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="fault" tick={{ fontSize: 10 }} width={150} tickFormatter={pretty} />
                <Tooltip formatter={(v) => [v, "cases"]} labelFormatter={(l) => pretty(String(l))} />
                <Bar dataKey="n">{stats.faults.map((f) => <Cell key={f.fault} fill={f.user_safe ? "#2b8a84" : "#f87171"} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
        <Section title="Conditions and provenance">
          <div className="card">
            <table className="tbl">
              <thead><tr><th>Condition</th><th>Language</th><th className="text-right">Variants</th></tr></thead>
              <tbody>{stats.conditions.map((c) => <tr key={c.condition}><td>{CONDITION_LABEL[c.condition]}</td><td>{c.lang_pair}</td><td className="text-right">{c.n}</td></tr>)}</tbody>
            </table>
            <div className="mt-5">
              <div className="text-sm font-medium">Provenance</div>
              <div className="mt-2 flex h-3 overflow-hidden rounded-full">
                {prov.map(([k, n], i) => <div key={k} style={{ width: `${(n / total) * 100}%` }} className={["bg-accent-500", "bg-amber-500", "bg-indigo-500"][i % 3]} />)}
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-xs muted">{prov.map(([k, n]) => <span key={k}>{k}: {n}</span>)}</div>
              <p className="mt-2 text-xs muted">Generated variants stay synthetic until native speakers correct them (transformed) or write them (genuine).</p>
            </div>
            <div className="mt-5 text-sm">
              <div className="font-medium">Gold action</div>
              <p className="mt-1 text-xs muted">{Object.entries(stats.gold_action).map(([k, n]) => `${pretty(k)} ${n}`).join(" · ")}</p>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}
