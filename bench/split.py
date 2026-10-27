"""Case-level train/val/test split, stratified by fault and seeded. All variants
of a case follow the case, so no paraphrase of a test case is seen during
development. Output: data/benchmark/splits.json."""

from __future__ import annotations

import json
import random
from collections import defaultdict

from bench.build_cases import load_config
from core.records import CASES_FILE, SPLITS_FILE, Case, read_jsonl


def split_cases(cases: list[Case], fractions: dict[str, float], seed: int) -> dict[str, list[str]]:
    by_fault: dict[str, list[str]] = defaultdict(list)
    for c in cases:
        by_fault[c.fault].append(c.case_id)
    rng = random.Random(seed)
    out = {name: [] for name in fractions}
    for fault in sorted(by_fault):
        ids = sorted(by_fault[fault])
        rng.shuffle(ids)
        n_train = round(len(ids) * fractions["train"])
        n_val = round(len(ids) * fractions["val"])
        out["train"] += ids[:n_train]
        out["val"] += ids[n_train:n_train + n_val]
        out["test"] += ids[n_train + n_val:]
    return {name: sorted(ids) for name, ids in out.items()}


def main() -> None:
    cfg = load_config()
    cases = read_jsonl(CASES_FILE, Case)
    splits = split_cases(cases, cfg["splits"], cfg["seed"])
    SPLITS_FILE.write_text(json.dumps({"seed": cfg["seed"], **splits}, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in splits.items()}, "->", SPLITS_FILE.name)


if __name__ == "__main__":
    main()
