import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PipelineDiagram from "../components/PipelineDiagram";
import { Findings, KeyStats } from "../components/Findings";
import { api, CONDITION_LABEL, pct, pretty, type Example, type PaperInfo, type Stats, type Summary } from "../api";

const TEAM = ["Saatwik Kumar Yadav", "Rachana Bhaskar Gowda", "Priyanshu Kumar Senapati", "S Md Adil Ahmed"];
const GITHUB = "https://github.com/skypank-coder/Query2Diagnose";
const TITLE = "Query2Diagnose: Uncertainty-Aware Interactive Troubleshooting from Noisy, Code-Mixed and Incomplete User Descriptions";

// Replays one saved dialogue from the latest run (GET /api/results/example), bubble by bubble.
function DialogueReplay({ ex }: { ex: Example | null }) {
  if (!ex) {
    return <div className="glass h-[420px] animate-pulse" aria-hidden />;
  }
  const steps = ex.turns.length * 2 + 3;
  const delay = (i: number) => ({ animationDelay: `${0.35 + i * 0.55}s` });
  return (
    <div className="glass p-5 text-sm text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] uppercase tracking-wider text-slate-400">
        <span>Replay · real dialogue from the saved run</span>
        <span className="font-mono normal-case">{ex.variant_id}</span>
      </div>
      <div className="mt-4 space-y-3">
        <div className="ml-auto max-w-[85%] animate-fade-up rounded-2xl rounded-br-sm bg-accent-500 px-4 py-2.5 text-white" style={delay(0)}>
          {ex.message}
        </div>
        {ex.changes.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1.5 animate-fade-up" style={delay(1)}>
            {ex.changes.slice(0, 4).map((c) => (
              <span key={c.original + c.normalized} className="rounded-full border border-amber-300/40 bg-amber-400/10 px-2 py-0.5 font-mono text-[11px] text-amber-200">
                {c.original} → {c.normalized}
              </span>
            ))}
          </div>
        )}
        {ex.turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <div className="max-w-[88%] animate-fade-up rounded-2xl rounded-bl-sm bg-white/10 px-4 py-2.5" style={delay(2 + i * 2)}>
              <div className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-300">{t.kind} question</div>
              {t.question}
            </div>
            <div className="ml-auto max-w-[70%] animate-fade-up rounded-2xl rounded-br-sm bg-accent-500/90 px-4 py-2 text-white" style={delay(3 + i * 2)}>
              {t.answer}
            </div>
          </div>
        ))}
        <div className="animate-fade-up rounded-xl border border-emerald-400/40 bg-emerald-400/10 p-3" style={delay(steps - 1)}>
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-emerald-200">✓ {ex.fault_name ?? pretty(ex.predicted)}</span>
            {ex.confidence != null && <span className="font-mono text-xs text-emerald-200">confidence {ex.confidence.toFixed(2)}</span>}
          </div>
          {ex.passages[0] && (
            <div className="mt-1 text-xs text-slate-300">
              Cited: {ex.passages[0].doc_title} → {ex.passages[0].section}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionHead({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-3xl">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl dark:text-white">{title}</h2>
      {children && <p className="mt-3 text-base leading-relaxed muted">{children}</p>}
    </div>
  );
}

export default function Home() {
  const [s, setS] = useState<Summary | null>(null);
  const [ex, setEx] = useState<Example | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [paper, setPaper] = useState<PaperInfo | null>(null);
  useEffect(() => {
    api.results().then(setS).catch(() => setS(null));
    api.example().then(setEx).catch(() => setEx(null));
    api.stats().then(setStats).catch(() => setStats(null));
    api.paper().then(setPaper).catch(() => setPaper(null));
  }, []);

  const unsafeFaults = stats?.faults.filter((f) => !f.user_safe).map((f) => f.name) ?? [];
  const langPairs = stats ? Array.from(new Set(stats.conditions.map((c) => c.lang_pair).filter((l) => l !== "none"))) : [];

  return (
    <div>
      {/* ---------------------------------------------------------------- hero */}
      <section className="relative isolate overflow-hidden">
        <img src="/images/hero-fridge.jpg" alt="An open refrigerator stocked with fruit, cheese and drinks"
             className="absolute inset-0 -z-20 h-full w-full object-cover" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-slate-950 via-slate-950/90 to-slate-950/55" />
        <div className="container-page grid items-center gap-12 py-16 lg:grid-cols-[1.1fr_1fr] lg:py-24 [&>*]:min-w-0">
          <div className="text-white">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-slate-200 backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-300" /> IEEE conference paper · RV University, Bengaluru
            </span>
            <h1 className="mt-6 font-serif text-4xl font-semibold leading-[1.08] tracking-tight md:text-6xl">
              When the message is messy,<br /><span className="text-accent-300">ask before you answer.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
              Query2Diagnose troubleshoots refrigerators from messages written the way people type: Kannada–English or
              Hindi–English, misspelt and half-finished. It keeps <em className="text-white">“did I understand you?”</em> apart
              from <em className="text-white">“which fault is it?”</em>, asks the question that settles the right doubt,
              cites its source, and hands dangerous repairs to a technician.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/demo" className="btn bg-accent-400 px-5 py-2.5 text-slate-950 hover:bg-accent-300">Try the live demo →</Link>
              <Link to="/results" className="btn-glass px-5 py-2.5">See the results</Link>
              <Link to="/paper" className="btn-glass px-5 py-2.5">Read the paper</Link>
            </div>
            {s && (
              <p className="mt-8 text-xs text-slate-400">
                Numbers on this site are read live from run <span className="font-mono">{s.run_id}</span> ({s.llm}); nothing is typed in by hand.
              </p>
            )}
          </div>
          <DialogueReplay ex={ex} />
        </div>
      </section>

      {/* ---------------------------------------------------- live headline numbers */}
      <section className="container-page relative -mt-8">
        {s ? <KeyStats s={s} /> : (
          <div className="card text-center text-sm muted">Results appear here once the API is running and a run has finished.</div>
        )}
      </section>

      {/* ------------------------------------------------------------ two doubts */}
      <section className="container-page py-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.15fr]">
          <div className="relative">
            <img src="/images/freezer-dial.jpg" alt="Inside a freezer compartment with its thermostat dial"
                 className="h-[460px] w-full rounded-3xl object-cover shadow-xl" loading="lazy" />
            <div className="absolute -bottom-6 left-6 right-6 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
              <div className="font-mono text-sm text-slate-800 dark:text-slate-100">fridge cooling agalla compressor sound ide</div>
              <div className="mt-1 text-xs muted">Kannada–English: <em>agalla</em> = “does not happen”, <em>sound ide</em> = “there is a sound”</div>
            </div>
          </div>
          <div>
            <SectionHead eyebrow="The idea" title="One message, two different doubts">
              A messy message leaves the assistant unsure about two separate things. Each calls for a different question,
              and Query2Diagnose measures both on every turn.
            </SectionHead>
            <div className="mt-8 space-y-4">
              <div className="card border-l-4 border-l-amber-500">
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-white">Linguistic doubt: what did the user say?</h3>
                  <span className="font-mono text-sm text-amber-600">H<sub>L</sub></span>
                </div>
                <p className="mt-1.5 text-sm muted">Does “sound ide” mean the compressor is humming normally, or that it makes a strange noise? The fix is a <strong className="text-slate-700 dark:text-slate-200">clarification</strong> question.</p>
              </div>
              <div className="card border-l-4 border-l-accent-500">
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-white">Diagnostic doubt: which fault is it?</h3>
                  <span className="font-mono text-sm text-accent-600">H<sub>D</sub></span>
                </div>
                <p className="mt-1.5 text-sm muted">The message is understood, but a torn door seal, a stopped fan and dusty coils all still fit. The fix is a <strong className="text-slate-700 dark:text-slate-200">diagnostic</strong> question.</p>
              </div>
              <p className="text-sm muted">
                One scoring rule picks whichever question is expected to remove the most uncertainty, after charging for the user's
                effort and for questions that people tend to misunderstand.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- how it works */}
      <section className="border-y border-slate-200 bg-slate-50 py-20 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="container-page grid items-center gap-12 lg:grid-cols-[1.1fr_1fr]">
          <div>
            <SectionHead eyebrow="How it works" title="From a messy message to a cited answer, or a referral" />
            <ol className="mt-8 space-y-5">
              {[
                ["Read it eight ways", "The language model reads the message eight times into a fixed 20-attribute schema, after a lexicon fixes Kannada, Hindi and misspelt words. Where the readings disagree, the system is unsure what was said."],
                ["Track both doubts", "A joint belief over readings and 15 faults gives H_L and H_D, and a fault state marks every attribute as confirmed, uncertain or unknown."],
                ["Ask the best question", "Clarification and diagnostic questions compete under one score: expected entropy drop minus effort and confusion costs."],
                ["Answer only with evidence", "It answers when one safe fault reaches 0.75 confidence and a retrieved iFixit passage supports it. Otherwise it refers to a technician with everything it has learned."],
              ].map(([t, d], i) => (
                <li key={t} className="flex gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-600 font-semibold text-white">{i + 1}</span>
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-white">{t}</div>
                    <p className="mt-1 text-sm leading-relaxed muted">{d}</p>
                  </div>
                </li>
              ))}
            </ol>
            <Link to="/method" className="btn-ghost mt-8">The equations →</Link>
          </div>
          <div className="card flex justify-center p-6"><PipelineDiagram /></div>
        </div>
      </section>

      {/* ------------------------------------------------------------- findings */}
      <section className="container-page py-20">
        <SectionHead eyebrow="Results" title="What we found, good and bad">
          Measured on the test split with a rule-based simulated user. We report the weak results as plainly as the strong ones.
        </SectionHead>
        <div className="mt-8">{s ? <Findings s={s} /> : <div className="card text-sm muted">Waiting for the API…</div>}</div>
        <Link to="/results" className="btn-primary mt-6">All tables and charts →</Link>
      </section>

      {/* ---------------------------------------------------------- safety band */}
      <section className="relative isolate overflow-hidden">
        <img src="/images/technician.jpg" alt="Hands using a screwdriver at a workbench" loading="lazy"
             className="absolute inset-0 -z-20 h-full w-full object-cover" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-l from-slate-950 via-slate-950/90 to-slate-950/40" />
        <div className="container-page flex justify-end py-24">
          <div className="max-w-xl text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-300">Safety first</p>
            <h2 className="mt-2 font-serif text-3xl font-semibold md:text-4xl">Some repairs are not for users</h2>
            <p className="mt-4 leading-relaxed text-slate-300">
              These faults are always referred to a qualified technician, along with every fact the assistant has already
              collected. The assistant never suggests a do-it-yourself fix for them.
            </p>
            {unsafeFaults.length > 0 && (
              <ul className="mt-4 flex flex-wrap gap-2">
                {unsafeFaults.map((f) => (
                  <li key={f} className="rounded-full border border-white/25 bg-white/10 px-3 py-1 text-xs text-slate-100 backdrop-blur">{f}</li>
                ))}
              </ul>
            )}
            {s && (
              <div className="mt-6 flex flex-wrap gap-8">
                <div><div className="font-serif text-4xl font-semibold text-accent-300">{pct(s.safety.q2d)}</div><div className="text-xs text-slate-400">unsafe DIY advice, Query2Diagnose</div></div>
                <div><div className="font-serif text-4xl font-semibold text-amber-300">{pct(s.safety.b2_llm_questions)}</div><div className="text-xs text-slate-400">same cases, LLM asking its own questions</div></div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- benchmark */}
      <section className="container-page py-20">
        <SectionHead eyebrow="The benchmark" title="Real sources, model-free answers, two language pairs">
          Built only from iFixit troubleshooting pages and ENERGY STAR guidance. Every case has one correct action fixed without
          consulting any model, and every case is written under several input conditions.
        </SectionHead>
        {stats && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [stats.n_cases.toLocaleString(), "cases", `${stats.faults.length} faults, ${unsafeFaults.length} unsafe for users`],
              [(stats.n_variants + stats.n_stress).toLocaleString(), "messages", `${stats.n_variants.toLocaleString()} variants + ${stats.n_stress} trilingual stress items`],
              [String(stats.conditions.length), "input conditions", stats.conditions.map((c) => CONDITION_LABEL[c.condition] ?? pretty(c.condition)).join(" · ")],
              [String(langPairs.length), "language pairs", langPairs.join(" and ") + ", on the same cases"],
            ].map(([k, label, hint]) => (
              <div key={label} className="card">
                <div className="kicker-num">{k}</div>
                <div className="mt-1 text-sm font-medium text-slate-700 dark:text-slate-200">{label}</div>
                <div className="mt-1 text-xs muted">{hint}</div>
              </div>
            ))}
          </div>
        )}
        <Link to="/benchmark" className="btn-ghost mt-6">Explore the benchmark →</Link>
      </section>

      {/* ---------------------------------------------------------------- paper */}
      <section className="border-t border-slate-200 bg-slate-50 py-20 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="container-page grid gap-10 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <p className="eyebrow">The paper</p>
            <h2 className="mt-2 font-serif text-2xl font-semibold leading-snug text-slate-900 md:text-3xl dark:text-white">{paper?.title ?? TITLE}</h2>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{(paper?.authors.length ? paper.authors : TEAM).join(", ")}</p>
            {paper?.abstract && <p className="mt-5 line-clamp-6 text-sm leading-relaxed muted">{paper.abstract}</p>}
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/paper" className="btn-primary">Read the paper</Link>
              <a href={GITHUB} className="btn-ghost" target="_blank" rel="noreferrer">Code and data on GitHub</a>
            </div>
          </div>
          <div className="card self-start">
            <div className="text-xs font-semibold uppercase tracking-wider muted">Team</div>
            <ul className="mt-4 space-y-3">
              {TEAM.map((name) => (
                <li key={name} className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-accent-400 to-accent-700 text-sm font-semibold text-white">
                    {name.split(" ").filter((p) => p.length > 1 || p === "S").map((p) => p[0]).slice(0, 2).join("")}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{name}</span>
                </li>
              ))}
            </ul>
            <p className="mt-5 border-t border-slate-200 pt-4 text-xs leading-relaxed muted dark:border-slate-800">
              B.Tech Computer Science and Engineering<br />School of Computer Science and Engineering, RV University, Bengaluru, India
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
