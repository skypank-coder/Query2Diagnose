// Typed client for the FastAPI backend (api/main.py). Every number the site
// shows comes from these endpoints; nothing is hard-coded.

export type Option = { value: string; label: string };
export type Question = { attribute: string; kind: "clarification" | "diagnostic" | "llm"; text: string; options: Option[] };
export type Hit = { passage_id: string; score: number | null; faults: string[]; text: string; url?: string; doc_title?: string; section?: string; license?: string };
export type Belief = { H_L: number; H_D: number; H: number; top: [string, number][]; n_interpretations: number };
export type Understanding = { normalized: string | null; changes: { original: string; normalized: string; source: string }[]; interpretations: { s: Record<string, string>; p: number }[]; n_valid_samples: number; H_L0: number };
export type Result = { predicted: string; top_fault: string | null; confidence: number; reason: string; turns: number; facts?: Record<string, string>; guidance?: string; passages: Hit[] };
export type Turn = {
  t: number;
  action: "ask" | "answer" | "refer";
  question: Question | null;
  belief?: Belief;
  fault_state?: Record<string, { status: "confirmed" | "uncertain" | "unknown"; value: string | null }>;
  hits?: Hit[];
  understanding?: Understanding;
  result?: Result;
};
export type FaultNames = Record<string, { name: string; user_safe: boolean }>;
export type Ci = [number, number, number];
export type Block = { n: number; macro_f1: Ci; accuracy: Ci; fault_accuracy: number; turns: { mean: number; median: number } };

export type Summary = {
  run_id: string; llm: string; clarity_llm?: string; created: string; profile?: string | null; status: string;
  seeds: number[]; n_cases: number; n_variants: number; cost_usd?: number; simulator: string;
  git: { commit: string; dirty: boolean }; tuned: Record<string, number>; agent_config: Record<string, unknown>;
  systems: string[]; conditions: string[];
  main: Record<string, Record<string, Block>>;
  by_lang: Record<string, Record<string, Block>>;
  robustness: Record<string, Record<string, number>>;
  reliability: Record<string, { ece: number; smooth_ece: number; brier: number; abstention_precision: number; abstention_recall: number; aurc: number; bins: { conf: number; acc: number; n: number }[]; selective: { coverage: number[]; accuracy: number[] } }>;
  safety: Record<string, number>;
  retrieval: Record<string, Record<string, number>>;
  understanding: Record<string, Record<string, number>>;
  questions: Record<string, { n_questions: number; informative: number; redundant: number; ig_per_turn: number | null }>;
  acc_vs_turns: Record<string, { turns: number; accuracy: number }[]>;
  trajectory: Record<string, Record<string, { H_L: number[]; H_D: number[]; n: number[] }>>;
  kn_vs_hi: Record<string, Record<string, { n: number; kn_f1: number; hi_f1: number; mcnemar: { p: number } }>>;
  significance: Record<string, Record<string, { n: number; mcnemar: { p: number; a_only: number; b_only: number }; p_holm: number; wilcoxon_turns: { p: number } }>>;
  stress: Record<string, Block>;
};

export type Stats = {
  n_cases: number; n_variants: number; n_stress: number; splits: Record<string, number>;
  conditions: { condition: string; lang_pair: string; n: number }[];
  provenance: Record<string, number>; gold_action: Record<string, number>;
  faults: { fault: string; name: string; user_safe: boolean; n: number }[];
  example: { case_id: string; fault: string; gold_action: string; variants: { condition: string; lang_pair: string; text: string; mentioned: string[] }[] };
  kappa: Record<string, { kappa: number; n: number }> | null;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw Object.assign(new Error(await res.text()), { status: res.status });
  return res.json() as Promise<T>;
}

export const api = {
  systems: () => call<{ default: string; llm: string; systems: { id: string; description: string }[] }>("/systems"),
  start: (message: string, system: string, lang: string) =>
    call<{ session_id: string; turn: Turn; fault_names: FaultNames }>("/session", { method: "POST", body: JSON.stringify({ message, system, lang }) }),
  answer: (id: string, text: string, value?: string) =>
    call<{ turn: Turn }>(`/session/${id}/answer`, { method: "POST", body: JSON.stringify({ text, value }) }),
  results: () => call<Summary>("/results/latest"),
  stats: () => call<Stats>("/benchmark/stats"),
};

export const SYSTEM_LABEL: Record<string, string> = {
  q2d: "Query2Diagnose", b1_direct: "B1 · direct", b2_llm_questions: "B2 · LLM questions", b3_infogain_dx: "B3 · info-gain (H_D)",
  q2d_minus_hl: "− H_L", q2d_minus_fault_state: "− fault state", q2d_minus_cost_clarity: "− cost / clarity", q2d_minus_normalisation: "− normalisation",
};
export const CONDITION_LABEL: Record<string, string> = {
  clean: "Clean", spelling: "Spelling", codemixed_kn: "Code-mixed kn", codemixed_hi: "Code-mixed hi",
  incomplete: "Incomplete", combined_kn: "Combined kn", combined_hi: "Combined hi", all: "All",
};
export const SYSTEM_COLOR: Record<string, string> = {
  q2d: "#1f6f6a", b1_direct: "#94a3b8", b2_llm_questions: "#c2410c", b3_infogain_dx: "#6366f1",
  q2d_minus_hl: "#0ea5e9", q2d_minus_fault_state: "#a855f7", q2d_minus_cost_clarity: "#22c55e", q2d_minus_normalisation: "#eab308",
};
export const pretty = (s: string) => s.replace(/_/g, " ");
