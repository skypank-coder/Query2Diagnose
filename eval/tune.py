"""Tune lambda and mu (eq. 3) on the validation split only (decision 11).

Grid lambda, mu in {0, 0.1, 0.25, 0.5, 1}; objective: action macro-F1 of Q2D,
ties broken by fewer mean turns. Understanding samples are cached, so after
the first grid point only selection changes and no new parsing calls are made.
Writes results/tuning/grid.json and results/tuning/best.json.

    python -I -m eval.tune [--max-cases 30] [--conditions clean codemixed_kn combined_kn] [--yes]
"""

from __future__ import annotations

import argparse
import itertools
import json

from core.clarity import load_clarity
from core.hypothesis import load_hypothesis_model
from core.llm import LLMClient, QuotaExhausted, Settings
from core.paths import RESULTS
from eval.metrics import macro_f1
from eval.run_experiment import TUNING_FILE, make_retriever, select_variants
from sim.user_simulator import UserSimulator
from systems.registry import build_systems

GRID = [0.0, 0.1, 0.25, 0.5, 1.0]


def main() -> None:
    ap = argparse.ArgumentParser(description="Tune lambda / mu on validation.")
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--conditions", nargs="+", default=["clean", "codemixed_kn", "combined_kn"])
    ap.add_argument("--K", type=int)
    ap.add_argument("--clarity-model")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    cfg = {"split": "val", "conditions": args.conditions, "max_cases": args.max_cases, "include_stress": False}
    variants, cases = select_variants(cfg)
    settings = Settings.from_env()
    llm = LLMClient(settings)
    clarity = load_clarity(args.clarity_model or settings.model) or {}
    k = args.K or 8
    print(f"tuning on {len(variants)} validation variants; first grid point needs ~{len(variants) * k} LLM calls "
          f"({llm.name}); the other {len(GRID) ** 2 - 1} reuse the cache")
    if not clarity:
        print("note: no A(q) estimate for this model yet; mu has no effect until one exists")
    if not args.yes and input("Run now? [y/N] ").strip().lower() != "y":
        return
    model, retriever = load_hypothesis_model(), make_retriever()
    grid = []
    try:
        for lam, mu in itertools.product(GRID, GRID):
            overrides = {"lambda_": lam, "mu": mu, **({"K": args.K} if args.K else {})}
            system = build_systems(["q2d"], llm, model, retriever, clarity, overrides)["q2d"]
            results = [system.run(v, UserSimulator(cases[v.case_id]), 0) for v in variants]
            f1 = macro_f1([cases[r.case_id].gold_action for r in results], [r.predicted for r in results])
            turns = sum(r.turns for r in results) / len(results)
            grid.append({"lambda_": lam, "mu": mu, "macro_f1": round(f1, 4), "mean_turns": round(turns, 3)})
            print(grid[-1], flush=True)
    except QuotaExhausted as e:
        print(f"stopped: {e}; rerun later, cached calls are free")
        return
    best = max(grid, key=lambda g: (g["macro_f1"], -g["mean_turns"]))
    out = RESULTS / "tuning"
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid.json").write_text(json.dumps({"llm": llm.name, "variants": len(variants), "conditions": args.conditions,
                                               "grid": grid}, indent=1), encoding="utf-8")
    TUNING_FILE.write_text(json.dumps({**best, "llm": llm.name}, indent=1), encoding="utf-8")
    print("best:", best)


if __name__ == "__main__":
    main()
