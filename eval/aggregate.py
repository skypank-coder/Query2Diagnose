"""Aggregate one finished run into results/runs/<run_id>/summary.json, the only
source the API, the website and eval/export_latex.py read numbers from.

    python -I -m eval.aggregate RUN_ID
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from functools import lru_cache
from statistics import mean

import numpy as np
import yaml

from core.belief import Belief
from core.hypothesis import load_hypothesis_model
from core.paths import DATA, RESULTS
from core.records import (
    CASES_FILE, CONDITIONS, NOISE_TYPE, REFER, STRESS_FILE, VARIANTS_FILE, Case, Variant, read_jsonl,
)
from core.schema import NOT_SURE, load_schema
from core.sources import load_passages
from eval import metrics as M
from eval.stats import bootstrap_ci, holm, mcnemar, wilcoxon_paired

RUNS = RESULTS / "runs"
AGENT_SYSTEMS = ("b3_infogain_dx", "q2d", "q2d_minus_hl", "q2d_minus_fault_state", "q2d_minus_cost_clarity",
                 "q2d_minus_normalisation")
BASELINES = ("b1_direct", "b2_llm_questions", "b3_infogain_dx")


@lru_cache(maxsize=1)
def _scenario_specific() -> dict[str, set[str]]:
    scenarios = yaml.safe_load((DATA / "benchmark" / "scenarios.yaml").read_text(encoding="utf-8"))
    return {s["id"]: set(s["attributes"]) - {"primary_symptom", "compartment_affected"}
            for ss in scenarios.values() for s in ss}


def load_run(run_dir) -> dict[str, list[dict]]:
    """Records per system, sorted by (variant, seed): parallel workers write in
    completion order, and the bootstrap must not depend on it."""
    records = {}
    for path in sorted(run_dir.glob("*.jsonl")):
        rs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        records[path.stem] = sorted(rs, key=lambda r: (r["variant_id"], r["seed"]))
    return records


def _ci(records, fn, n=1000) -> list[float]:
    point, low, high = bootstrap_ci(records, fn, lambda r: r["case_id"], n=n)
    return [round(point, 4), round(low, 4), round(high, 4)]


def _f1(rs, cases):
    return M.macro_f1([cases[r["case_id"]].gold_action for r in rs], [r["predicted"] for r in rs])


def _acc(rs, cases):
    return M.accuracy([cases[r["case_id"]].gold_action for r in rs], [r["predicted"] for r in rs])


def _fault_ok(r, cases) -> bool:
    return r["top_fault"] == cases[r["case_id"]].fault


def _block(rs, cases, n_boot=1000) -> dict:
    if not rs:
        return {}
    return {"n": len(rs),
            "macro_f1": _ci(rs, lambda x: _f1(x, cases), n_boot),
            "accuracy": _ci(rs, lambda x: _acc(x, cases), n_boot),
            "fault_accuracy": round(mean(_fault_ok(r, cases) for r in rs), 4),
            "turns": M.turn_stats([r["turns"] for r in rs])}


def _forced_action(turn: dict, tau: float, unsafe: set[str]) -> str:
    top, p = turn["belief"]["top"][0]
    supported = any(top in h["faults"] for h in turn["hits"])
    return top if (p >= tau and top not in unsafe and supported) else REFER


def _shadow_ig(r: dict, case: Case, variant: Variant, model) -> list[float]:
    """Information gain per answered question for an observer that starts from
    the gold facts of the message and applies the simulator's answers (same
    yardstick for every question-asking system)."""
    known = {a: case.attributes[a] for a in variant.mentioned_attributes if a != "device"}
    belief = Belief(model, [known], np.ones(1))
    gains = []
    for t in r["transcript"]:
        attribute = (t.get("question") or {}).get("attribute")
        value = t.get("sim_value")
        if attribute in model.schema.attributes and value not in (None,) and attribute not in known:
            before = belief.h_d
            belief.update(attribute, value if value != NOT_SURE else NOT_SURE)
            gains.append(before - belief.h_d)
    return gains


def _asked(r: dict) -> list[str]:
    return [t["question"]["attribute"] for t in r["transcript"] if t.get("question")]


def summarize(run_dir) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records = load_run(run_dir)
    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    variants = {v.variant_id: v for v in read_jsonl(VARIANTS_FILE, Variant) + read_jsonl(STRESS_FILE, Variant)}
    schema, model = load_schema(), load_hypothesis_model(manifest["config"].get("hypothesis_weights"))
    unsafe = schema.unsafe_faults
    tau = manifest["agent_config"]["tau"]
    t_max = manifest["agent_config"]["T_max"]
    dups = M.near_duplicates(load_passages())
    systems = [s for s in manifest["config"]["systems"] if s in records]
    conditions = [c for c in CONDITIONS if c in manifest["config"]["conditions"]]

    out: dict = {"run_id": manifest["run_id"], "llm": manifest["llm"], "clarity_llm": manifest.get("clarity_llm"),
                 "created": manifest["created"], "profile": manifest["config"].get("profile"),
                 "status": manifest["status"], "seeds": manifest["config"]["seeds"], "n_cases": manifest["n_cases"],
                 "n_variants": manifest["n_variants"], "cost_usd": manifest.get("cost_usd"),
                 "git": manifest["git"], "tuned": manifest.get("tuned", {}), "agent_config": manifest["agent_config"],
                 "simulator": manifest["config"]["simulator"]["mode"],
                 "hypothesis_weights": manifest["config"].get("hypothesis_weights"),
                 "systems": systems, "conditions": conditions}
    main, by_lang, by_noise, robustness, reliability, safety, retrieval = {}, {}, {}, {}, {}, {}, {}
    understanding, questions, acc_vs_turns, trajectory, provenance, stress = {}, {}, {}, {}, {}, {}

    for s in systems:
        rs_all = records[s]
        rs = [r for r in rs_all if r["condition"] in conditions]
        main[s] = {c: _block([r for r in rs if r["condition"] == c], cases) for c in conditions}
        main[s]["all"] = _block(rs, cases)
        by_lang[s] = {lp: _block([r for r in rs if r["lang_pair"] == lp], cases, 300)
                      for lp in ("none", "kn-en", "hi-en") if any(r["lang_pair"] == lp for r in rs)}
        noise: dict[str, list] = defaultdict(list)
        for r in rs:
            noise[NOISE_TYPE[r["condition"]]].append(r)
        by_noise[s] = {k: round(_f1(v, cases), 4) for k, v in noise.items()}
        robustness[s] = {k: round(v, 4) for k, v in
                         M.robustness_drop({c: main[s][c]["macro_f1"][0] for c in conditions if main[s][c]}).items()}
        stress_rs = [r for r in rs_all if r["condition"] == "mixed_kn_hi"]
        if stress_rs:
            stress[s] = _block(stress_rs, cases, 300)

        conf = [r["confidence"] for r in rs]
        ok = [_fault_ok(r, cases) for r in rs]
        gold_refer = [cases[r["case_id"]].gold_action == REFER for r in rs]
        pred_refer = [r["predicted"] == REFER for r in rs]
        sel = M.selective_curve(conf, ok)
        step = max(1, len(sel["coverage"]) // 50)
        reliability[s] = {"ece": round(M.ece(conf, ok), 4), "smooth_ece": round(M.smooth_ece(conf, ok), 4),
                          "brier": round(M.brier(conf, ok), 4),
                          **{f"abstention_{k}": round(v, 4) for k, v in M.abstention_pr(gold_refer, pred_refer).items()},
                          "aurc": round(sel["aurc"], 4), "bins": M.calibration_bins(conf, ok),
                          "selective": {"coverage": sel["coverage"][::step], "accuracy": sel["accuracy"][::step]}}
        safety[s] = round(M.unsafe_advice_rate([cases[r["case_id"]].fault in unsafe for r in rs],
                                               [r["predicted"] for r in rs]), 4)
        gold_pids = [dups[cases[r["case_id"]].source_passage_id] for r in rs]
        retrieved = [r["extras"].get("retrieved") or r["passage_ids"] for r in rs]
        retrieval[s] = {f"recall@{k}": round(M.recall_at_k(gold_pids, retrieved, k), 4) for k in (1, 3, 5)}

        asked = [_asked(r) for r in rs]
        rates = M.question_rates(asked, [set(variants[r["variant_id"]].mentioned_attributes) for r in rs],
                                 [_scenario_specific()[cases[r["case_id"]].scenario_id] for r in rs])
        gains = [g for r in rs for g in _shadow_ig(r, cases[r["case_id"]], variants[r["variant_id"]], model)]
        questions[s] = {**{k: round(v, 4) for k, v in rates.items()},
                        "ig_per_turn": round(float(np.mean(gains)), 4) if gains else None}

        prov: dict[str, list] = defaultdict(list)
        for r in rs:
            prov[variants[r["variant_id"]].provenance].append(r)
        provenance[s] = {k: round(_f1(v, cases), 4) for k, v in prov.items()}

        if s in AGENT_SYSTEMS:
            pred_slots, gold_slots, status_items = [], [], []
            for r in rs:
                v, c = variants[r["variant_id"]], cases[r["case_id"]]
                u = r["extras"].get("understanding") or {}
                top = (u.get("interpretations") or [{"s": {}}])[0]["s"]
                pred_slots.append(set(top.items()))
                gold_slots.append({(a, c.attributes[a]) for a in v.mentioned_attributes if a != "device"})
                fs = r["transcript"][0]["fault_state"]
                for a, st in fs.items():
                    if a == "device":
                        continue
                    status_items.append((st["status"], a in v.mentioned_attributes, st["value"] == c.attributes[a]))
            prf = M.slot_prf(pred_slots, gold_slots)
            understanding[s] = {**{f"slot_{k}": round(v, 4) for k, v in prf.items()},
                                "status_accuracy": round(M.status_accuracy(status_items), 4)}
            curve = []
            for budget in range(t_max + 1):
                preds = []
                for r in rs:
                    tr = r["transcript"]
                    preds.append(r["predicted"] if budget >= len(tr) - 1 else _forced_action(tr[budget], tau, unsafe))
                curve.append({"turns": budget, "accuracy": round(M.accuracy(
                    [cases[r["case_id"]].gold_action for r in rs], preds), 4)})
            acc_vs_turns[s] = curve
            traj = {}
            for group, conds in (("clean", {"clean"}), ("codemixed", {"codemixed_kn", "codemixed_hi"}),
                                 ("combined", {"combined_kn", "combined_hi"})):
                sub = [r for r in rs if r["condition"] in conds]
                if not sub:
                    continue
                traj[group] = {"H_L": [], "H_D": [], "n": []}
                for t in range(t_max + 1):
                    at = [r["transcript"][t]["belief"] for r in sub if len(r["transcript"]) > t]
                    if at:
                        traj[group]["H_L"].append(round(mean(b["H_L"] for b in at), 4))
                        traj[group]["H_D"].append(round(mean(b["H_D"] for b in at), 4))
                        traj[group]["n"].append(len(at))
            trajectory[s] = traj
        else:
            acc_vs_turns[s] = [{"turns": round(mean(r["turns"] for r in rs), 2), "accuracy": round(_acc(rs, cases), 4)}]

    # Kannada vs Hindi on the same cases (paired).
    kn_vs_hi = {}
    for s in systems:
        rs = records[s]
        kn_vs_hi[s] = {}
        for noise in ("codemixed", "combined"):
            kn = {(r["case_id"], r["seed"]): r for r in rs if r["condition"] == f"{noise}_kn"}
            hi = {(r["case_id"], r["seed"]): r for r in rs if r["condition"] == f"{noise}_hi"}
            keys = sorted(set(kn) & set(hi))
            if not keys:
                continue
            a = [kn[k]["predicted"] == cases[k[0]].gold_action for k in keys]
            b = [hi[k]["predicted"] == cases[k[0]].gold_action for k in keys]
            kn_vs_hi[s][noise] = {"n": len(keys), "kn_f1": round(_f1([kn[k] for k in keys], cases), 4),
                                  "hi_f1": round(_f1([hi[k] for k in keys], cases), 4),
                                  "mcnemar": mcnemar(a, b)}

    # Q2D vs each baseline: McNemar (action correctness) and Wilcoxon (turns), Holm per scope.
    significance = {}
    if "q2d" in records:
        q = {(r["variant_id"], r["seed"]): r for r in records["q2d"] if r["condition"] in conditions}
        for scope in ["all"] + conditions:
            tests, raw = {}, {}
            for b in BASELINES:
                if b not in records:
                    continue
                other = {(r["variant_id"], r["seed"]): r for r in records[b] if r["condition"] in conditions}
                keys = [k for k in q if k in other and (scope == "all" or q[k]["condition"] == scope)]
                if not keys:
                    continue
                qa = [q[k]["predicted"] == cases[q[k]["case_id"]].gold_action for k in keys]
                ba = [other[k]["predicted"] == cases[other[k]["case_id"]].gold_action for k in keys]
                tests[b] = {"n": len(keys), "mcnemar": mcnemar(qa, ba),
                            "wilcoxon_turns": wilcoxon_paired([q[k]["turns"] for k in keys],
                                                              [other[k]["turns"] for k in keys])}
                raw[b] = tests[b]["mcnemar"]["p"]
            for b, p in holm(raw).items():
                tests[b]["p_holm"] = round(p, 6)
            significance[scope] = tests

    out.update(main=main, by_lang=by_lang, by_noise=by_noise, robustness=robustness, reliability=reliability,
               safety=safety, retrieval=retrieval, understanding=understanding, questions=questions,
               acc_vs_turns=acc_vs_turns, trajectory=trajectory, kn_vs_hi=kn_vs_hi, significance=significance,
               provenance=provenance, stress=stress)
    relevance = run_dir / "relevance.json"
    if relevance.exists():
        out["relevance"] = json.loads(relevance.read_text(encoding="utf-8"))
    (run_dir / "summary.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_id")
    args = ap.parse_args()
    summarize(RUNS / args.run_id)
    print(f"-> results/runs/{args.run_id}/summary.json")


if __name__ == "__main__":
    main()
