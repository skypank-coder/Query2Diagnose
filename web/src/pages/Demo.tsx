import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError, pretty, SYSTEM_LABEL, type FaultNames, type Hit, type Recording, type RecordingInfo, type Result, type Turn } from "../api";
import { Bar } from "../components/ui";

// Messages rehearsed against the live API: their LLM calls are cached, so they answer instantly.
const INSTANT = [
  ["Kannada–English", "freezer alli frost jaasti aagide, compressor run aagtide, door rubber sari ide"],
  ["Kannada–English", "fridge cooling agalla compressor sound ide"],
  ["Hindi–English", "fridge bilkul band pada hai, na light hai na display"],
] as const;
const STATUS_STYLE = {
  confirmed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  uncertain: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  unknown: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};
const KIND_STYLE: Record<string, string> = {
  clarification: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  diagnostic: "bg-accent-100 text-accent-700 dark:bg-accent-700/30 dark:text-accent-400",
  llm: "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
};

type Msg = { role: "user" | "system"; text: string; kind?: string; result?: Result };
type Mode = "checking" | "live" | "replay";

function Passage({ hit }: { hit: Hit }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-700">
      <div className="font-medium">{hit.doc_title}{hit.section ? ` — ${hit.section}` : ""}</div>
      <p className="mt-1 line-clamp-4 muted">{hit.text}</p>
      {hit.url && <a className="mt-1 inline-block text-accent-600 hover:underline dark:text-accent-400" href={hit.url} target="_blank" rel="noreferrer">{hit.license?.startsWith("CC") ? "iFixit · CC BY-NC-SA 3.0" : "Source"} ↗</a>}
    </div>
  );
}

function ResultCard({ result, names }: { result: Result; names: FaultNames }) {
  const refer = result.predicted === "REFER";
  const top = result.top_fault ? names[result.top_fault]?.name ?? pretty(result.top_fault) : null;
  return (
    <div className={`animate-fade-up rounded-xl border p-4 ${refer ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30" : "border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/30"}`}>
      <div className="text-xs font-semibold uppercase tracking-wide">{refer ? "Referral to a technician" : "Likely cause"}</div>
      <div className="mt-1 font-serif text-lg font-semibold">{refer ? (top ? `Most likely: ${top}` : "No safe conclusion") : top}</div>
      <div className="mt-1 text-xs muted">confidence {result.confidence.toFixed(2)} · {result.turns} question(s) · {pretty(result.reason)}</div>
      {refer && <p className="mt-2 text-sm">A qualified technician should inspect the fridge. The facts collected so far are passed on so they do not start from scratch.</p>}
      {result.facts && Object.keys(result.facts).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">{Object.entries(result.facts).filter(([a]) => a !== "device").map(([a, v]) => (
          <span key={a} className="rounded bg-white/70 px-2 py-0.5 text-xs dark:bg-slate-900/60">{pretty(a)}: {pretty(v)}</span>))}</div>
      )}
      {result.guidance && <p className="mt-2 text-sm">{result.guidance}</p>}
      {!refer && result.passages.length > 0 && (
        <div className="mt-3 space-y-2"><div className="text-xs font-medium">Cited passage</div><Passage hit={result.passages[0]} /></div>
      )}
    </div>
  );
}

function BeliefPanel({ turn, first, names }: { turn: Turn | null; first: Turn | null; names: FaultNames }) {
  const belief = turn?.belief;
  const understanding = first?.understanding;
  if (!belief) {
    return (
      <div className="card text-sm muted">
        {turn ? "This baseline keeps no structured belief, so there is nothing to show here." : "The belief over interpretations and faults appears here as the conversation goes."}
        {turn?.hits && turn.hits.length > 0 && <div className="mt-3 space-y-2">{turn.hits.slice(0, 3).map((h) => <Passage key={h.passage_id} hit={h} />)}</div>}
      </div>
    );
  }
  return (
    <>
      <div className="card space-y-3">
        <div className="flex items-baseline justify-between">
          <h3 className="font-semibold">Uncertainty (bits)</h3>
          <span className="text-xs muted">turn {turn!.t} · {belief.n_interpretations} reading(s) kept</span>
        </div>
        <Bar value={belief.H_L} max={3} color="bg-amber-500" label={<><span>Linguistic H<sub>L</sub>: what was said?</span><span>{belief.H_L.toFixed(2)}</span></>} />
        <Bar value={belief.H_D} max={Math.log2(15)} color="bg-accent-500" label={<><span>Diagnostic H<sub>D</sub>: which fault?</span><span>{belief.H_D.toFixed(2)}</span></>} />
      </div>
      <div className="card space-y-2">
        <h3 className="font-semibold">Top faults</h3>
        {belief.top.map(([z, p]) => (
          <Bar key={z} value={p} max={1} color={names[z]?.user_safe === false ? "bg-red-400" : "bg-accent-500"}
            label={<><span>{names[z]?.name ?? pretty(z)}{names[z]?.user_safe === false && <span className="ml-1 text-[10px] font-semibold text-red-600">REFER</span>}</span><span>{p.toFixed(2)}</span></>} />
        ))}
      </div>
      {understanding && (
        <div className="card">
          <h3 className="font-semibold">How the message was read</h3>
          {understanding.changes.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {understanding.changes.slice(0, 8).map((c, i) => (
                <span key={i} className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 font-mono text-[11px] text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300">{c.original} → {c.normalized}</span>
              ))}
            </div>
          )}
          <div className="mt-3 space-y-2">
            {understanding.interpretations.slice(0, 3).map((it, i) => (
              <div key={i} className="text-xs">
                <span className="font-mono font-semibold">p(s|x) = {it.p.toFixed(2)}</span>
                <div className="mt-0.5 flex flex-wrap gap-1">{Object.entries(it.s).map(([a, v]) => <span key={a} className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">{pretty(a)}: {pretty(v)}</span>)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {turn?.fault_state && (
        <details className="card">
          <summary className="cursor-pointer font-semibold">Fault state <span className="text-xs font-normal muted">(every attribute: confirmed, uncertain or unknown)</span></summary>
          <table className="mt-2 w-full text-xs">
            <tbody>
              {Object.entries(turn.fault_state).filter(([a]) => a !== "device").map(([a, s]) => (
                <tr key={a} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="py-1 pr-2">{pretty(a)}</td>
                  <td className="py-1 text-right"><span className={`rounded px-1.5 py-0.5 ${STATUS_STYLE[s.status]}`}>{s.status === "confirmed" ? pretty(s.value ?? "") : s.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </>
  );
}

export default function Demo() {
  const [mode, setMode] = useState<Mode>("checking");
  const [systems, setSystems] = useState<{ id: string; description: string }[]>([]);
  const [llm, setLlm] = useState("");
  const [retrieval, setRetrieval] = useState("");
  const [system, setSystem] = useState("q2d");
  const [lang, setLang] = useState("en");
  const [input, setInput] = useState("");
  const [message, setMessage] = useState("");
  const [session, setSession] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [turn, setTurn] = useState<Turn | null>(null);
  const [first, setFirst] = useState<Turn | null>(null);
  const [names, setNames] = useState<FaultNames>({});
  const [busy, setBusy] = useState(false);
  const [waited, setWaited] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [recs, setRecs] = useState<RecordingInfo[]>([]);
  const [rec, setRec] = useState<Recording | null>(null);
  const [step, setStep] = useState(0);
  const [autoplay, setAutoplay] = useState(false);
  const [history, setHistory] = useState<{ text: string; value?: string | null }[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [params] = useSearchParams();
  const scroller = useRef<HTMLDivElement>(null);
  const retry = useRef<(() => void) | null>(null);

  useEffect(() => {
    api.live().then((live) => {
      setMode(live ? "live" : "replay");
      api.systems().then((s) => { setSystems(s.systems); setLlm(s.llm); setRetrieval(s.retrieval ?? ""); }).catch(() => undefined);
      api.recordings().then(setRecs).catch(() => { if (!live) setError("No recorded dialogues found."); });
    });
  }, []);
  // The server loads the model in the background after it starts; show when it is ready.
  useEffect(() => {
    if (mode !== "live" || ready) return;
    const poll = () => api.health().then((h) => { if (h?.ready) setReady(true); });
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, [mode, ready]);
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);
  useEffect(() => {
    if (!busy) { setWaited(0); return; }
    const id = setInterval(() => setWaited((w) => w + 1), 1000);
    return () => clearInterval(id);
  }, [busy]);

  const show = (t: Turn) => {
    setTurn(t);
    if (t.question) setMsgs((m) => [...m, { role: "system", text: t.question!.text, kind: t.question!.kind }]);
    if (t.result) setMsgs((m) => [...m, { role: "system", text: "", kind: "final", result: t.result }]);
  };
  const reset = () => {
    setAutoplay(false); setMsgs([]); setTurn(null); setFirst(null); setSession(null); setRec(null); setStep(0);
    setError(null); setNotice(null); setHistory([]); retry.current = null;
  };
  const reconnecting = (n: number) => setNotice(`The server is not answering; reconnecting… (try ${n})`);
  const friendly = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Please try again.");

  // If the live model fails on a dialogue we also have a recording of, and the
  // answers so far match the recorded ones, continue from the recording.
  async function fallBack(msgText: string, sys: string, answers: { text: string; value?: string | null }[]): Promise<boolean> {
    const info = recs.find((r) => r.message === msgText && r.system === sys);
    if (!info) return false;
    let r: Recording;
    try { r = await api.recording(info.id); } catch { return false; }
    const same = answers.every((a, i) => a.value != null && r.steps[i]?.answer?.value === a.value);
    if (!same || answers.length >= r.steps.length) return false;
    setRec(r); setNames(r.fault_names); setStep(answers.length);
    if (answers.length === 0) setFirst(r.steps[0].turn);
    show(r.steps[answers.length].turn);
    setNotice("The live model did not answer, so this continues from a recorded run of the same dialogue.");
    return true;
  }

  async function start(text: string, sys = system) {
    if (!text.trim()) return;
    reset();
    setBusy(true); setMessage(text); setSystem(sys);
    setMsgs([{ role: "user", text }]);
    retry.current = () => start(text, sys);
    try {
      const r = await api.start(text, sys, lang, reconnecting);
      setNotice(null); setSession(r.session_id); setNames(r.fault_names); setFirst(r.turn); show(r.turn); setInput("");
    } catch (e) {
      setNotice(null);
      if (!(await fallBack(text, sys, []))) setError(friendly(e));
    } finally { setBusy(false); }
  }

  async function reply(text: string, value?: string) {
    if (!session || (!text.trim() && !value)) return;
    setBusy(true); setError(null); setNotice(null);
    setMsgs((m) => [...m, { role: "user", text }]);
    retry.current = () => { setMsgs((m) => m.slice(0, -1)); reply(text, value); };
    try {
      const r = await api.answer(session, text, value, { message, system, lang, history }, reconnecting);
      setNotice(null); setHistory((h) => [...h, { text, value }]); show(r.turn); setInput("");
    } catch (e) {
      setNotice(null);
      if (!(await fallBack(message, system, [...history, { text, value }]))) setError(friendly(e));
    } finally { setBusy(false); }
  }

  async function play(id: string) {
    reset();
    try {
      const r = await api.recording(id);
      setRec(r); setNames(r.fault_names); setMessage(r.message); setSystem(r.system); setStep(0);
      setMsgs([{ role: "user", text: r.message }]);
      setFirst(r.steps[0].turn); show(r.steps[0].turn);
    } catch { setError("This recorded dialogue could not be loaded."); }
  }

  function advance() {
    if (!rec) return;
    const answer = rec.steps[step].answer;
    if (!answer) return;
    setMsgs((m) => [...m, { role: "user", text: answer.text }]);
    show(rec.steps[step + 1].turn);
    setStep(step + 1);
  }

  useEffect(() => {
    const id = params.get("play");
    if (mode === "replay" && id && recs.some((r) => r.id === id) && !rec) { play(id).then(() => setAutoplay(true)); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, recs]);
  useEffect(() => {
    if (!autoplay || !rec || turn?.action !== "ask" || !rec.steps[step]?.answer) return;
    const id = setTimeout(advance, 1400);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoplay, rec, step, turn]);

  const asking = turn?.action === "ask";
  const done = !!turn?.result;
  const replaying = !!rec;
  const expected = rec?.steps[step]?.answer?.value;
  const siblings = rec ? recs.filter((r) => r.message === rec.message && r.id !== rec.id) : [];

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
        <span><strong>Research prototype, not repair advice.</strong> Refrigerant, sealed-system, compressor and live-electric faults are always referred to a technician.</span>
        {mode === "replay" && <span className="rounded-full bg-amber-200 px-2.5 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-800 dark:text-amber-100">Replay mode · recorded real dialogues</span>}
        {mode === "live" && <span className="rounded-full bg-emerald-200 px-2.5 py-0.5 text-xs font-semibold text-emerald-900 dark:bg-emerald-800 dark:text-emerald-100">{ready ? `Live · ${llm}${retrieval === "tfidf" ? " · TF-IDF retrieval" : ""}` : "Live · loading the model…"}</span>}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr] [&>*]:min-w-0">
        {/* chat: fixed height, scrolls inside, controls pinned at the bottom */}
        <div className="card flex h-[75vh] min-h-[480px] flex-col p-0 lg:sticky lg:top-20 lg:h-[calc(100vh-8.5rem)]">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3 dark:border-slate-800">
            {mode === "live" && !replaying ? (
              <>
                <select value={system} onChange={(e) => setSystem(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700" aria-label="System">
                  {systems.map((s) => <option key={s.id} value={s.id} className="text-slate-900">{SYSTEM_LABEL[s.id] ?? s.id}</option>)}
                </select>
                <select value={lang} onChange={(e) => setLang(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700" aria-label="Question language">
                  <option value="en" className="text-slate-900">Questions in English</option>
                  <option value="kn" className="text-slate-900">Kannada–English</option>
                  <option value="hi" className="text-slate-900">Hindi–English</option>
                </select>
              </>
            ) : (
              <span className="text-sm font-medium">{rec ? SYSTEM_LABEL[rec.system] : "Pick a recorded dialogue"}</span>
            )}
            {msgs.length > 0 && <button className="btn-ghost ml-auto px-3 py-1 text-xs" onClick={reset}>New</button>}
          </div>

          <div ref={scroller} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
            {msgs.length === 0 && mode === "live" && (
              <div className="py-2">
                <p className="text-sm muted">Describe a refrigerator problem the way you would text it. These examples answer instantly:</p>
                <div className="mt-3 flex flex-col gap-2">
                  {INSTANT.map(([tag, text]) => (
                    <button key={text} className="rounded-xl border border-slate-200 px-3 py-2 text-left text-sm transition hover:border-accent-500 hover:bg-accent-50 dark:border-slate-700 dark:hover:bg-accent-700/10" onClick={() => start(text)}>
                      <span className="mr-2 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">instant</span>
                      <span className="mr-1.5 text-[10px] uppercase muted">{tag}</span>{text}
                    </button>
                  ))}
                </div>
                <p className="mt-4 text-xs muted">A new message of your own takes about a minute: the model reads it eight times on a free API tier.</p>
                {retrieval === "tfidf" && (
                  <p className="mt-2 rounded-lg bg-sky-50 px-3 py-2 text-xs text-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
                    This hosted copy retrieves passages with TF-IDF, because the multilingual-e5 model used in the paper is too large
                    for a serverless function, so some answers differ from the paper's runs. The recorded dialogues below were made
                    with the paper's setup.
                  </p>
                )}
                {recs.length > 0 && (
                  <div className="mt-5">
                    <p className="text-sm muted">Or replay a recorded dialogue (click the highlighted answers, or press ▶):</p>
                    <div className="mt-2 flex flex-col gap-2">
                      {recs.map((r) => (
                        <button key={r.id} className="rounded-xl border border-dashed border-slate-300 px-3 py-2 text-left text-sm transition hover:border-accent-500 hover:bg-accent-50 dark:border-slate-700 dark:hover:bg-accent-700/10" onClick={() => play(r.id)}>
                          <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">recorded</span>
                          <span className="text-[11px] font-semibold uppercase tracking-wide text-accent-600 dark:text-accent-400">{SYSTEM_LABEL[r.system]}</span>
                          <span className="ml-1.5 font-mono text-[13px]">{r.message}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            {msgs.length === 0 && mode === "replay" && (
              <div className="py-2">
                <p className="text-sm muted">This hosted copy replays real dialogues recorded from the system; nothing here is scripted by hand. Pick one and click the highlighted answer to continue:</p>
                <div className="mt-3 flex flex-col gap-2">
                  {recs.map((r) => (
                    <button key={r.id} className="rounded-xl border border-slate-200 px-3 py-2 text-left text-sm transition hover:border-accent-500 hover:bg-accent-50 dark:border-slate-700 dark:hover:bg-accent-700/10" onClick={() => play(r.id)}>
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-accent-600 dark:text-accent-400">{SYSTEM_LABEL[r.system]} · {r.label}</div>
                      <div className="mt-0.5 font-mono text-[13px]">{r.message}</div>
                    </button>
                  ))}
                </div>
                <p className="mt-4 text-xs muted">To type your own messages, run the project locally (see the README on GitHub).</p>
              </div>
            )}
            {msgs.map((m, i) => m.role === "user" ? (
              <div key={i} className="flex animate-fade-up justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-sm bg-accent-600 px-4 py-2 text-sm text-white">{m.text}</div></div>
            ) : m.result ? (
              <ResultCard key={i} result={m.result} names={names} />
            ) : (
              <div key={i} className="max-w-[90%] animate-fade-up">
                <span className={`mb-1 inline-block rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${KIND_STYLE[m.kind ?? "llm"]}`}>
                  {m.kind === "llm" ? "LLM question" : `${m.kind} question`}
                </span>
                <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2 text-sm dark:bg-slate-800">{m.text}</div>
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-sm muted">
                <span className="inline-flex gap-1"><span className="h-2 w-2 animate-bounce rounded-full bg-accent-500" /><span className="h-2 w-2 animate-bounce rounded-full bg-accent-500 [animation-delay:150ms]" /><span className="h-2 w-2 animate-bounce rounded-full bg-accent-500 [animation-delay:300ms]" /></span>
                {turn ? "Updating the belief…" : `Reading the message eight ways… ${waited}s`}
              </div>
            )}
          </div>

          {/* pinned controls */}
          <div className="border-t border-slate-200 px-5 py-3 dark:border-slate-800">
            {asking && turn?.question?.options && turn.question.options.length > 0 && (
              <div className="mb-3">
                <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px] font-medium uppercase tracking-wide muted">
                  <span>{replaying ? "Click the highlighted answer" : "Tap an answer, or type your own"}</span>
                  {replaying && !autoplay && <button className="btn-ghost px-2 py-0.5 text-[11px] normal-case" onClick={() => setAutoplay(true)}>▶ Play the rest</button>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {turn.question.options.map((o) => {
                    const isNext = replaying && o.value === expected;
                    return (
                      <button key={o.value} disabled={busy || (replaying && !isNext)}
                        onClick={() => (replaying ? advance() : reply(o.label, o.value))}
                        className={`chip ${isNext ? "border-accent-600 bg-accent-600 text-white ring-4 ring-accent-200 dark:ring-accent-700/40" : "border-accent-400 text-accent-700 hover:bg-accent-50 disabled:opacity-40 dark:text-accent-400 dark:hover:bg-accent-700/20"}`}>
                        {o.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {done && (
              <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
                <span className="muted">Same message with:</span>
                {!replaying
                  ? ["q2d", "b3_infogain_dx", "b2_llm_questions", "b1_direct"].filter((s) => s !== system).map((s) => (
                      <button key={s} className="btn-ghost px-3 py-1" onClick={() => start(message, s)}>{SYSTEM_LABEL[s]}</button>
                    ))
                  : siblings.map((r) => <button key={r.id} className="btn-ghost px-3 py-1" onClick={() => play(r.id)}>{SYSTEM_LABEL[r.system]}</button>)}
                <button className="btn-ghost px-3 py-1" onClick={reset}>Another example</button>
              </div>
            )}
            {notice && (
              <div className="mb-3 rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-xs text-sky-900 dark:border-sky-700 dark:bg-sky-950/40 dark:text-sky-200">{notice}</div>
            )}
            {error && (
              <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
                <span className="flex-1">{error}</span>
                {retry.current && <button className="btn-ghost px-3 py-1 text-xs" onClick={() => { setError(null); retry.current?.(); }}>Try again</button>}
                <button className="btn-ghost px-3 py-1 text-xs" onClick={reset}>Use an instant example</button>
              </div>
            )}
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); session && asking ? reply(input) : start(input); }}>
              <input value={input} onChange={(e) => setInput(e.target.value)} disabled={busy || mode !== "live" || replaying}
                placeholder={mode !== "live" ? "Typing needs the local server; pick a recorded dialogue above" : replaying ? "Click the highlighted answer above, or press New" : asking ? "Answer in your own words (any language)…" : "fridge cooling agalla, compressor sound ide…"}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-accent-500 disabled:opacity-60 dark:border-slate-700" />
              <button className="btn-primary" disabled={busy || mode !== "live" || replaying || !input.trim()}>{asking ? "Answer" : "Diagnose"}</button>
            </form>
          </div>
        </div>

        {/* belief: sticky beside the chat, scrolls on its own */}
        <aside className="space-y-4 lg:sticky lg:top-20 lg:max-h-[calc(100vh-8.5rem)] lg:overflow-y-auto lg:pr-1">
          <BeliefPanel turn={turn} first={first} names={names} />
        </aside>
      </div>
    </div>
  );
}
