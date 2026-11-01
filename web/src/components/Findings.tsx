import { f2, pct, pval, type Summary } from "../api";
import { CountUp } from "./Animated";

// Headline numbers and findings, computed from the run summary on every load.

function pick(s: Summary) {
  const all = (x: string) => s.main[x]?.all;
  const drop = (x: string) => Math.max(...Object.values(s.robustness[x] ?? { none: 0 }));
  const traj = s.trajectory.q2d ?? {};
  return {
    unsafe: (x: string) => s.safety[x],
    ece: (x: string) => s.reliability[x]?.ece,
    fault: (x: string) => all(x)?.fault_accuracy,
    acc: (x: string) => all(x)?.accuracy?.[0],
    f1: (x: string) => all(x)?.macro_f1?.[0],
    pHolm: (x: string) => s.significance.all?.[x]?.p_holm,
    drop,
    hl0: (g: string) => traj[g]?.H_L?.[0],
    absP: s.reliability.q2d?.abstention_precision,
    absR: s.reliability.q2d?.abstention_recall,
    dialogues: s.n_variants * s.seeds.length * s.systems.length,
  };
}

export function KeyStats({ s }: { s: Summary }) {
  const v = pick(s);
  const cards = [
    { k: <CountUp value={(v.unsafe("q2d") ?? 0) * 100} decimals={1} suffix="%" />, label: "unsafe DIY advice", vs: `vs ${pct(v.unsafe("b1_direct"))} and ${pct(v.unsafe("b2_llm_questions"))} for the LLM baselines` },
    { k: <CountUp value={v.ece("q2d") ?? 0} decimals={2} />, label: "calibration error (ECE)", vs: `vs ${f2(v.ece("b2_llm_questions"))} and ${f2(v.ece("b1_direct"))}; lower is better` },
    { k: <CountUp value={(v.fault("q2d") ?? 0) * 100} decimals={1} suffix="%" />, label: "right fault ranked first", vs: `vs ${pct(v.fault("b2_llm_questions"))} for the LLM that asks questions` },
    { k: <CountUp value={v.dialogues} grouping />, label: "simulated dialogues", vs: `${s.seeds.length} seeds · ${s.systems.length} systems · ${s.llm}` },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="card animate-fade-up">
          <div className="kicker-num">{c.k}</div>
          <div className="mt-1 text-sm font-medium text-slate-700 dark:text-slate-200">{c.label}</div>
          <div className="mt-1 text-xs muted">{c.vs}</div>
        </div>
      ))}
    </div>
  );
}

export function Findings({ s }: { s: Summary }) {
  const v = pick(s);
  const works = [
    `Never advised a do-it-yourself repair on an unsafe fault (${pct(v.unsafe("q2d"))}); the LLM baselines did in ${pct(v.unsafe("b1_direct"))} and ${pct(v.unsafe("b2_llm_questions"))} of those cases.`,
    `Confidence it can trust: calibration error ${f2(v.ece("q2d"))} against ${f2(v.ece("b2_llm_questions"))} and ${f2(v.ece("b1_direct"))}.`,
    `Correct fault ranked first in ${pct(v.fault("q2d"))} of dialogues against ${pct(v.fault("b2_llm_questions"))}; action accuracy ${f2(v.acc("q2d"))} vs ${f2(v.acc("b2_llm_questions"))} (McNemar, Holm-corrected, ${pval(v.pHolm("b2_llm_questions"))}).`,
    `Steady under noise: its largest macro-F1 drop from clean input is ${f2(v.drop("q2d"))}, against ${f2(v.drop("b1_direct"))} for the direct-answer LLM.`,
  ];
  const notYet = [
    `Refers too often: REFER recall ${f2(v.absR)} but precision ${f2(v.absP)}, so action macro-F1 is ${f2(v.f1("q2d"))} against ${f2(v.f1("b2_llm_questions"))} for B2.`,
    `Separating linguistic uncertainty gave no measurable gain: without H_L macro-F1 is ${f2(v.f1("q2d_minus_hl"))}, and Q2D vs B3 is not significant (${pval(v.pHolm("b3_infogain_dx"))}).`,
    `Why: at the first turn H_L is ${f2(v.hl0("clean"))} bits on clean English and ${f2(v.hl0("combined"))} on the noisiest messages, so sampling tracks the parser's own variation more than the noise in the message.`,
  ];
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="card border-l-4 border-l-emerald-500">
        <h3 className="flex items-center gap-2 font-serif text-xl font-semibold text-slate-900 dark:text-white">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-sm text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">✓</span>
          What works
        </h3>
        <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {works.map((t) => <li key={t} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />{t}</li>)}
        </ul>
      </div>
      <div className="card border-l-4 border-l-amber-500">
        <h3 className="flex items-center gap-2 font-serif text-xl font-semibold text-slate-900 dark:text-white">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-100 text-sm text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">!</span>
          What does not work yet
        </h3>
        <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {notYet.map((t) => <li key={t} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />{t}</li>)}
        </ul>
      </div>
    </div>
  );
}
