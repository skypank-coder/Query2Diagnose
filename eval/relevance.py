"""Human relevance ratings of the questions systems ask (1-5, two raters).

    python -I -m eval.relevance export [--run RUN_ID] [--n 60]
    python -I -m eval.relevance score RATER_A.csv RATER_B.csv [--run RUN_ID]

`export` samples questions evenly across systems into
results/runs/<run>/relevance_sheet.csv (system names hidden from raters in
the `item` order; the key is kept in relevance_key.json). `score` computes the
quadratic-weighted Cohen's kappa and the mean rating per system and writes
relevance.json, which eval/aggregate.py includes in summary.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict

from core.paths import RESULTS
from core.records import STRESS_FILE, VARIANTS_FILE, Variant, read_jsonl
from eval.aggregate import load_run
from eval.agreement import weighted_kappa
from eval.export_latex import latest_run


def export(run_id: str, n: int) -> None:
    run_dir = RESULTS / "runs" / run_id
    variants = {v.variant_id: v for v in read_jsonl(VARIANTS_FILE, Variant) + read_jsonl(STRESS_FILE, Variant)}
    pool = defaultdict(list)
    for system, records in load_run(run_dir).items():
        for r in records:
            for t in r["transcript"]:
                q = (t.get("question") or {}).get("text")
                if q:
                    pool[system].append((r["variant_id"], q))
    rng = random.Random(0)
    per = max(1, n // max(1, len(pool)))
    items = [(s, *x) for s, xs in pool.items() for x in rng.sample(xs, min(per, len(xs)))]
    rng.shuffle(items)
    with (run_dir / "relevance_sheet.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "customer_message", "question", "rating_1_to_5", "rater"])
        for i, (_, vid, q) in enumerate(items):
            w.writerow([i, variants[vid].text, q, "", ""])
    (run_dir / "relevance_key.json").write_text(json.dumps({i: s for i, (s, _, _) in enumerate(items)}), encoding="utf-8")
    print(f"{len(items)} questions -> {run_dir / 'relevance_sheet.csv'}")


def score(run_id: str, a_path: str, b_path: str) -> None:
    run_dir = RESULTS / "runs" / run_id
    key = {int(k): v for k, v in json.loads((run_dir / "relevance_key.json").read_text(encoding="utf-8")).items()}

    def load(p):
        with open(p, encoding="utf-8") as f:
            return {int(r["item"]): int(r["rating_1_to_5"]) for r in csv.DictReader(f) if r["rating_1_to_5"].strip()}
    a, b = load(a_path), load(b_path)
    common = sorted(set(a) & set(b))
    by_system = defaultdict(list)
    for i in common:
        by_system[key[i]].append((a[i] + b[i]) / 2)
    result = {"n": len(common), "weighted_kappa": round(weighted_kappa([a[i] for i in common], [b[i] for i in common],
                                                                       [1, 2, 3, 4, 5]), 4),
              "mean_rating": {s: round(sum(v) / len(v), 3) for s, v in by_system.items()}}
    (run_dir / "relevance.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser(description="Question relevance ratings.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--run")
    e.add_argument("--n", type=int, default=60)
    s = sub.add_parser("score")
    s.add_argument("rater_a")
    s.add_argument("rater_b")
    s.add_argument("--run")
    args = ap.parse_args()
    run_id = args.run or latest_run()
    if run_id is None:
        print("no finished run yet")
        return
    export(run_id, args.n) if args.cmd == "export" else score(run_id, args.rater_a, args.rater_b)


if __name__ == "__main__":
    main()
