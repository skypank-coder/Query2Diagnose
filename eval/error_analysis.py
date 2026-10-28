"""Bucket Query2Diagnose failures by cause and write results/error_analysis.md
with real transcript examples (2-3 per bucket).

Buckets, checked in order (first match wins):
  misparsed_negation      the top interpretation flips a stated yes/no fact
  missed_codemixed_token  code-mixed input and a stated fact is missing from the parse
  wrong_clarification     a clarification answer was parsed to a different value than the user meant
  retrieval_miss          the right fault reached tau but no retrieved passage supported it
  premature_stop          answered with a wrong fault
  hypothesis_model_gap    everything else: the model could not reach tau / ranked the wrong fault

    python -I -m eval.error_analysis [--run RUN_ID] [--system q2d]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from core.paths import RESULTS
from core.records import CASES_FILE, REFER, STRESS_FILE, VARIANTS_FILE, Case, Variant, read_jsonl
from eval.aggregate import load_run
from eval.export_latex import latest_run

ORDER = ["misparsed_negation", "missed_codemixed_token", "wrong_clarification", "retrieval_miss",
         "premature_stop", "hypothesis_model_gap"]


def bucket(r: dict, case: Case, variant: Variant) -> str:
    u = r["extras"].get("understanding") or {}
    top = (u.get("interpretations") or [{"s": {}}])[0]["s"]
    stated = [a for a in variant.mentioned_attributes if a != "device"]
    for a in stated:
        gold = case.attributes[a]
        if gold in ("yes", "no") and top.get(a) in ("yes", "no") and top[a] != gold:
            return "misparsed_negation"
    if variant.lang_pair in ("kn-en", "hi-en", "kn-hi-en") and any(a not in top for a in stated):
        return "missed_codemixed_token"
    for t in r["transcript"]:
        q = t.get("question") or {}
        if q.get("kind") == "clarification" and t.get("sim_value") and t.get("answer_value") != t["sim_value"]:
            return "wrong_clarification"
    if r.get("reason") == "unsupported" and r["top_fault"] == case.fault:
        return "retrieval_miss"
    if r["predicted"] != REFER and r["predicted"] != case.gold_action:
        return "premature_stop"
    return "hypothesis_model_gap"


def describe(r: dict, case: Case, variant: Variant) -> str:
    u = r["extras"].get("understanding") or {}
    lines = [f"- **{variant.variant_id}** ({variant.condition}): \"{variant.text}\"",
             f"  - gold fault `{case.fault}`, gold action `{case.gold_action}`; predicted `{r['predicted']}` "
             f"(top `{r['top_fault']}`, p={r['confidence']}, {r['turns']} turns, {r['reason']})"]
    if u.get("normalized"):
        lines.append(f"  - normalised: \"{u['normalized']}\"")
    for i in (u.get("interpretations") or [])[:2]:
        lines.append(f"  - interpretation p={i['p']}: `{json.dumps(i['s'])}`")
    for t in r["transcript"]:
        q = t.get("question")
        if q:
            lines.append(f"  - t={t['t']} {q['kind']} `{q['attribute']}`: \"{q['text']}\" -> \"{t.get('answer_text')}\" "
                         f"(parsed `{t.get('answer_value')}`, meant `{t.get('sim_value')}`; "
                         f"H_L={t['belief']['H_L']}, H_D={t['belief']['H_D']})")
    return "\n".join(lines)


def analyse(run_id: str, system: str = "q2d") -> str:
    records = load_run(RESULTS / "runs" / run_id).get(system, [])
    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    variants = {v.variant_id: v for v in read_jsonl(VARIANTS_FILE, Variant) + read_jsonl(STRESS_FILE, Variant)}
    buckets: dict[str, list] = defaultdict(list)
    failures = [r for r in records if r["predicted"] != cases[r["case_id"]].gold_action]
    for r in failures:
        buckets[bucket(r, cases[r["case_id"]], variants[r["variant_id"]])].append(r)
    out = [f"# Error analysis: `{system}` in run `{run_id}`", "",
           f"{len(failures)} of {len(records)} dialogues end with the wrong action. Buckets are checked in the "
           "order below; each failure counts once.", "", "| Cause | Failures | Share |", "|---|---|---|"]
    for b in ORDER:
        n = len(buckets[b])
        out.append(f"| {b} | {n} | {n / len(failures):.0%} |" if failures else f"| {b} | 0 | - |")
    for b in ORDER:
        if buckets[b]:
            out += ["", f"## {b}", ""]
            out += [describe(r, cases[r["case_id"]], variants[r["variant_id"]]) for r in buckets[b][:3]]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Bucket Q2D failures by cause.")
    ap.add_argument("--run")
    ap.add_argument("--system", default="q2d")
    args = ap.parse_args()
    run_id = args.run or latest_run()
    if run_id is None:
        print("no finished run yet")
        return
    path = RESULTS / "error_analysis.md"
    path.write_text(analyse(run_id, args.system), encoding="utf-8")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
