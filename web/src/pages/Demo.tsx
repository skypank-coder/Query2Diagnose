import { useEffect, useRef, useState } from "react";
import { api, pretty, SYSTEM_LABEL, type FaultNames, type Hit, type Result, type Turn } from "../api";
import { Bar } from "../components/ui";

const EXAMPLES: [string, string][] = [
  ["Kannada–English", "fridge cooling agalla compressor sound ide"],
  ["Kannada–English", "freezer alli tumba frost katkondide, hinde gode mele frost ide"],
  ["Hindi–English", "fridge mein cooling nahi ho rahi, compressor ki awaaz aa rahi hai"],
  ["Hindi–English", "fridge ke neeche paani aa raha hai"],
  ["English", "My fridge is not cooling and it makes a clicking sound every few minutes"],
  ["Typos", "fridg coolong agalla, olagr light bartice"],
];
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
    <div className={`mt-2 rounded-xl border p-4 ${refer ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30" : "border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/30"}`}>
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

export default function Demo() {
  const [systems, setSystems] = useState<{ id: string; description: string }[]>([]);
  const [llm, setLlm] = useState("");
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
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => { api.systems().then((s) => { setSystems(s.systems); setLlm(s.llm); }).catch(() => setError("The API is not reachable. Start it with `make api`.")); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs]);

  const show = (t: Turn) => {
    setTurn(t);
    if (t.question) setMsgs((m) => [...m, { role: "system", text: t.question!.text, kind: t.question!.kind }]);
    if (t.result) setMsgs((m) => [...m, { role: "system", text: "", kind: "final", result: t.result }]);
  };

  async function start(text: string, sys = system) {
    if (!text.trim()) return;
    setBusy(true); setError(null); setMessage(text); setSystem(sys);
    setMsgs([{ role: "user", text }]); setTurn(null); setFirst(null);
    try {
      const r = await api.start(text, sys, lang);
      setSession(r.session_id); setNames(r.fault_names); setFirst(r.turn); show(r.turn); setInput("");
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function reply(text: string, value?: string) {
    if (!session || (!text.trim() && !value)) return;
    setBusy(true); setError(null);
    setMsgs((m) => [...m, { role: "user", text }]);
    try { show((await api.answer(session, text, value)).turn); setInput(""); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const asking = turn?.action === "ask";
  const done = !!turn?.result;
  const belief = turn?.belief;
  const understanding = first?.understanding;

  return (
    <div>
      <div className="mb-5 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
        <strong>Research prototype, not repair advice.</strong> Faults involving refrigerant, the sealed system, the compressor, its relays or live electrics are always referred to a technician. Unplug the fridge before touching anything inside.
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <div className="card flex min-h-[560px] flex-col">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
            <select value={system} onChange={(e) => setSystem(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700" aria-label="System">
              {systems.map((s) => <option key={s.id} value={s.id} className="text-slate-900">{SYSTEM_LABEL[s.id] ?? s.id}</option>)}
            </select>
            <select value={lang} onChange={(e) => setLang(e.target.value)} className="rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700" aria-label="Question language">
              <option value="en" className="text-slate-900">Questions in English</option>
              <option value="kn" className="text-slate-900">Kannada–English</option>
              <option value="hi" className="text-slate-900">Hindi–English</option>
            </select>
            {llm && <span className="ml-auto text-xs muted">LLM: {llm}</span>}
          </div>
          <p className="mt-2 text-xs muted">{systems.find((s) => s.id === system)?.description}</p>

          <div className="mt-3 flex-1 space-y-3 overflow-y-auto">
            {msgs.length === 0 && (
              <div className="py-6">
                <p className="text-sm muted">Describe a refrigerator problem the way you would text it, or try an example:</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {EXAMPLES.map(([tag, text]) => (
                    <button key={text} className="chip border-slate-300 text-left hover:border-accent-500 hover:text-accent-700 dark:border-slate-700" onClick={() => start(text)}>
                      <span className="mr-1.5 text-[10px] uppercase muted">{tag}</span>{text}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {msgs.map((m, i) => m.role === "user" ? (
              <div key={i} className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-sm bg-accent-600 px-4 py-2 text-sm text-white">{m.text}</div></div>
            ) : m.result ? (
              <ResultCard key={i} result={m.result} names={names} />
            ) : (
              <div key={i} className="max-w-[90%]">
                <span className={`mb-1 inline-block rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${KIND_STYLE[m.kind ?? "llm"]}`}>
                  {m.kind === "llm" ? "LLM question" : m.kind}
                </span>
                <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2 text-sm dark:bg-slate-800">{m.text}</div>
              </div>
            ))}
            {busy && <div className="text-sm muted animate-pulse">thinking…</div>}
            <div ref={bottom} />
          </div>

          {asking && turn?.question?.options && turn.question.options.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {turn.question.options.map((o) => (
                <button key={o.value} disabled={busy} onClick={() => reply(o.label, o.value)}
                  className="chip border-accent-400 text-accent-700 hover:bg-accent-50 dark:text-accent-400 dark:hover:bg-accent-700/20">{o.label}</button>
              ))}
            </div>
          )}
          {error && <div className="mt-2 text-sm text-red-600">{error}</div>}
          <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); session && asking ? reply(input) : start(input); }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} disabled={busy}
              placeholder={asking ? "Answer in your own words (any language)…" : "fridge cooling agalla, compressor sound ide…"}
              className="flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-accent-500 dark:border-slate-700" />
            <button className="btn-primary" disabled={busy || !input.trim()}>{asking ? "Answer" : "Diagnose"}</button>
          </form>
          {done && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="muted">Same message with:</span>
              {["q2d", "b3_infogain_dx", "b2_llm_questions", "b1_direct"].filter((s) => s !== system).map((s) => (
                <button key={s} className="btn-ghost px-3 py-1" onClick={() => start(message, s)}>{SYSTEM_LABEL[s]}</button>
              ))}
              <button className="btn-ghost px-3 py-1" onClick={() => { setMsgs([]); setTurn(null); setSession(null); }}>New</button>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          {!belief && (
            <div className="card text-sm muted">
              {turn ? "This baseline keeps no structured belief, so there is nothing to show here." : "The belief over interpretations and faults appears here as the conversation goes."}
              {turn?.hits && turn.hits.length > 0 && <div className="mt-3 space-y-2">{turn.hits.slice(0, 3).map((h) => <Passage key={h.passage_id} hit={h} />)}</div>}
            </div>
          )}
          {belief && (
            <>
              <div className="card space-y-3">
                <h3 className="font-semibold">Uncertainty (bits)</h3>
                <Bar value={belief.H_L} max={3} color="bg-amber-500" label={<><span>Linguistic H<sub>L</sub></span><span>{belief.H_L.toFixed(2)}</span></>} />
                <Bar value={belief.H_D} max={Math.log2(15)} color="bg-accent-500" label={<><span>Diagnostic H<sub>D</sub></span><span>{belief.H_D.toFixed(2)}</span></>} />
                <p className="text-xs muted">Turn {turn!.t} · {belief.n_interpretations} interpretation(s) kept</p>
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
                  {understanding.normalized && <p className="mt-1 text-xs muted">Gloss: <span className="font-mono">{understanding.normalized}</span></p>}
                  <div className="mt-2 space-y-2">
                    {understanding.interpretations.slice(0, 4).map((it, i) => (
                      <div key={i} className="text-xs">
                        <span className="font-mono font-semibold">p(s|x) = {it.p.toFixed(2)}</span>
                        <div className="mt-0.5 flex flex-wrap gap-1">{Object.entries(it.s).map(([a, v]) => <span key={a} className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">{pretty(a)}: {pretty(v)}</span>)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {turn?.fault_state && (
                <div className="card">
                  <h3 className="font-semibold">Fault state</h3>
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
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
