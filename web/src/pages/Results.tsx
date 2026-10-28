import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, CONDITION_LABEL, SYSTEM_COLOR, SYSTEM_LABEL, type Block, type Summary } from "../api";
import { Empty, Loading, Section, Stat } from "../components/ui";

const MAIN = ["b1_direct", "b2_llm_questions", "b3_infogain_dx", "q2d"];
const ABL = ["q2d", "q2d_minus_hl", "q2d_minus_fault_state", "q2d_minus_cost_clarity", "q2d_minus_normalisation"];
const f2 = (x: number | null | undefined) => (x == null ? "—" : x.toFixed(2));

function Cell({ b }: { b?: Block }) {
  if (!b || !b.macro_f1) return <td className="text-center muted">—</td>;
  const [p, lo, hi] = b.macro_f1;
  return (
    <td className="text-center tabular-nums">
      <div>{p.toFixed(2)}<span className="text-xs muted"> ±{((hi - lo) / 2).toFixed(2)}</span></div>
      <div className="text-[11px] muted">{b.turns.mean.toFixed(1)} turns</div>
    </td>
  );
}

function Chart({ children, height = 280 }: { children: React.ReactElement; height?: number }) {
  return <div className="card" style={{ height }}><ResponsiveContainer>{children}</ResponsiveContainer></div>;
}

export default function Results() {
  const [s, setS] = useState<Summary | null>(null);
  const [state, setState] = useState<"loading" | "none" | "error" | "ok">("loading");
  useEffect(() => {
    api.results().then((r) => { setS(r); setState("ok"); })
      .catch((e: { status?: number }) => setState(e.status === 404 ? "none" : "error"));
  }, []);
  if (state === "loading") return <Loading what="Loading results" />;
  if (state === "error") return <Empty title="Results unavailable">The API is not reachable. Start it with <code>make api</code>.</Empty>;
  if (state === "none" || !s) return (
    <Empty title="No finished run yet">
      Results appear here only after an experiment run completes; nothing is shown from placeholders.
      Run <code>make pilot</code> (fits the Groq free tier) or <code>make experiments</code>, then reload.
    </Empty>
  );

  const conds = [...s.conditions, "all"];
  const main = MAIN.filter((x) => s.main[x]);
  const robustness = s.conditions.map((c) => ({ c: CONDITION_LABEL[c], ...Object.fromEntries(main.map((x) => [x, s.main[x][c]?.macro_f1?.[0]])) }));
  const traj = s.trajectory.q2d ?? {};
  const trajData = Array.from({ length: Math.max(0, ...Object.values(traj).map((g) => g.H_D.length)) }, (_, t) => ({
    t, ...Object.fromEntries(Object.entries(traj).flatMap(([g, v]) => [[`H_L ${g}`, v.H_L[t]], [`H_D ${g}`, v.H_D[t]]])),
  }));
  const sig = s.significance.all ?? {};

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-serif text-3xl font-semibold text-slate-900 dark:text-white">Results</h1>
        {s.profile === "pilot" && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">Pilot run — not the full grid</span>}
      </div>
      <p className="mt-2 text-sm muted">Run <span className="font-mono">{s.run_id}</span> · {s.llm} · {new Date(s.created).toLocaleString()} · commit {s.git.commit.slice(0, 7)}{s.git.dirty ? " (dirty)" : ""}</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Cases / variants" value={`${s.n_cases} / ${s.n_variants}`} hint={`test split · seeds ${s.seeds.join(", ")}`} />
        <Stat label="Simulator" value={s.simulator} hint="rule-based, answers from hidden ground truth" />
        <Stat label="λ / μ" value={`${s.agent_config.lambda_} / ${s.agent_config.mu}`} hint={s.tuned.lambda_ !== undefined ? "tuned on validation" : "defaults (not tuned)"} />
        <Stat label="Cost" value={`$${(s.cost_usd ?? 0).toFixed(2)}`} hint={`paid-tier estimate · A(q) by ${s.clarity_llm ?? s.llm}`} />
      </div>

      <Section title="Main results" subtitle="Action macro-F1 (REFER is a class) ± half-width of the 95% case-level bootstrap CI; mean turns below.">
        <div className="card overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>System</th>{conds.map((c) => <th key={c} className="text-center">{CONDITION_LABEL[c]}</th>)}</tr></thead>
            <tbody>{main.map((x) => <tr key={x}><td className="font-medium">{SYSTEM_LABEL[x]}</td>{conds.map((c) => <Cell key={c} b={s.main[x][c]} />)}</tr>)}</tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Robustness" subtitle="Macro-F1 per input condition">
          <Chart>
            <LineChart data={robustness} margin={{ right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="c" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => v?.toFixed(3)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {main.map((x) => <Line key={x} dataKey={x} name={SYSTEM_LABEL[x]} stroke={SYSTEM_COLOR[x]} strokeWidth={x === "q2d" ? 3 : 1.5} dot />)}
            </LineChart>
          </Chart>
        </Section>
        <Section title="Accuracy vs turns" subtitle="Agent systems truncated at each turn budget; B1/B2 at their mean turns">
          <Chart>
            <LineChart margin={{ right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis type="number" dataKey="turns" domain={[0, "dataMax"]} tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => v?.toFixed(3)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {main.filter((x) => s.acc_vs_turns[x]).map((x) => <Line key={x} data={s.acc_vs_turns[x]} dataKey="accuracy" name={SYSTEM_LABEL[x]} stroke={SYSTEM_COLOR[x]} strokeWidth={x === "q2d" ? 3 : 1.5} dot={{ r: 4 }} />)}
            </LineChart>
          </Chart>
        </Section>
        <Section title="Calibration" subtitle="Confidence in the top fault vs top-fault accuracy">
          <Chart>
            <LineChart margin={{ right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis type="number" dataKey="conf" domain={[0, 1]} tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#94a3b8" strokeDasharray="4 4" />
              <Tooltip formatter={(v: number) => v?.toFixed(3)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {main.map((x) => <Line key={x} data={s.reliability[x].bins} dataKey="acc" name={SYSTEM_LABEL[x]} stroke={SYSTEM_COLOR[x]} dot />)}
            </LineChart>
          </Chart>
        </Section>
        <Section title="Linguistic vs diagnostic uncertainty" subtitle="Query2Diagnose: mean H_L and H_D per turn, clean vs code-mixed input">
          {trajData.length ? (
            <Chart>
              <LineChart data={trajData} margin={{ right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="t" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} unit=" b" />
                <Tooltip formatter={(v: number) => v?.toFixed(3)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {Object.keys(traj).flatMap((g, i) => [
                  <Line key={`l${g}`} dataKey={`H_L ${g}`} stroke="#d97706" strokeDasharray={["", "6 3", "2 3"][i]} dot />,
                  <Line key={`d${g}`} dataKey={`H_D ${g}`} stroke="#1f6f6a" strokeDasharray={["", "6 3", "2 3"][i]} dot />,
                ])}
              </LineChart>
            </Chart>
          ) : <div className="card text-sm muted">Not in this run.</div>}
        </Section>
      </div>

      <Section title="Ablations" subtitle="Each row removes one component of Query2Diagnose">
        <div className="card overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>Variant</th><th className="text-center">Macro-F1 (all)</th><th className="text-center">Code-mixed F1</th><th className="text-center">Turns</th><th className="text-center">ECE</th><th className="text-center">Unsafe advice</th></tr></thead>
            <tbody>{ABL.filter((x) => s.main[x]).map((x) => {
              const cm = ["codemixed_kn", "codemixed_hi"].map((c) => s.main[x][c]?.macro_f1?.[0]).filter((v): v is number => v != null);
              return (
                <tr key={x}><td className="font-medium">{SYSTEM_LABEL[x]}</td><Cell b={s.main[x].all} />
                  <td className="text-center">{cm.length ? f2(cm.reduce((a, b) => a + b, 0) / cm.length) : "—"}</td>
                  <td className="text-center">{s.main[x].all.turns.mean.toFixed(1)}</td>
                  <td className="text-center">{f2(s.reliability[x].ece)}</td><td className="text-center">{f2(s.safety[x])}</td></tr>
              );
            })}</tbody>
          </table>
        </div>
      </Section>

      <Section title="Reliability, safety, retrieval and questions">
        <div className="card overflow-x-auto">
          <table className="tbl">
            <thead><tr><th>System</th><th>ECE</th><th>smECE</th><th>Brier</th><th>Abst. P</th><th>Abst. R</th><th>Unsafe</th><th>R@1</th><th>R@5</th><th>IG / turn</th><th>Informative Q</th></tr></thead>
            <tbody>{s.systems.map((x) => {
              const r = s.reliability[x], q = s.questions[x];
              return (
                <tr key={x} className="tabular-nums"><td className="font-medium">{SYSTEM_LABEL[x]}</td><td>{f2(r.ece)}</td><td>{f2(r.smooth_ece)}</td><td>{f2(r.brier)}</td>
                  <td>{f2(r.abstention_precision)}</td><td>{f2(r.abstention_recall)}</td><td>{f2(s.safety[x])}</td>
                  <td>{f2(s.retrieval[x]["recall@1"])}</td><td>{f2(s.retrieval[x]["recall@5"])}</td>
                  <td>{f2(q?.ig_per_turn)}</td><td>{q?.n_questions ? f2(q.informative) : "—"}</td></tr>
              );
            })}</tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Kannada vs Hindi (paired cases)">
          <div className="card overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>System</th><th>Noise</th><th>n</th><th>kn-en F1</th><th>hi-en F1</th><th>McNemar p</th></tr></thead>
              <tbody>{s.systems.flatMap((x) => Object.entries(s.kn_vs_hi[x] ?? {}).map(([noise, d]) => (
                <tr key={x + noise} className="tabular-nums"><td>{SYSTEM_LABEL[x]}</td><td>{noise}</td><td>{d.n}</td><td>{f2(d.kn_f1)}</td><td>{f2(d.hi_f1)}</td><td>{d.mcnemar.p.toFixed(3)}</td></tr>
              )))}</tbody>
            </table>
          </div>
        </Section>
        <Section title="Query2Diagnose vs baselines" subtitle="Exact McNemar on action correctness, Holm-corrected; Wilcoxon on turns">
          <div className="card overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Baseline</th><th>n</th><th>Q2D only</th><th>Baseline only</th><th>p (Holm)</th><th>Turns p</th></tr></thead>
              <tbody>{Object.entries(sig).map(([b, t]) => (
                <tr key={b} className="tabular-nums"><td>{SYSTEM_LABEL[b]}</td><td>{t.n}</td><td>{t.mcnemar.a_only}</td><td>{t.mcnemar.b_only}</td><td>{t.p_holm.toFixed(4)}</td><td>{t.wilcoxon_turns.p.toFixed(4)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
      </div>
    </div>
  );
}
