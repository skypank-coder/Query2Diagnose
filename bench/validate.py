"""Validate the benchmark and compute annotator agreement.

    python -I -m bench.validate                       # schema + consistency + duplicates
    python -I -m bench.validate --kappa A.csv B.csv   # Cohen's kappa on a shared sheet

Kappa input: two filled copies of annotation/export/kappa_sheet.csv; every
`label_*` column is compared on the variants both annotators labelled.
The result is written to data/benchmark/annotation/kappa.json for the dataset
statistics table.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from bench.build_cases import load_config, load_scenarios
from core.records import (
    BENCHMARK, CASES_FILE, LANG_PAIR, REFER, STRESS_FILE, VARIANTS_FILE, Case, Variant, load_splits, read_jsonl,
)
from core.schema import load_schema
from core.sources import load_fault_passages, load_passages
from eval.agreement import cohen_kappa

KAPPA_FILE = BENCHMARK / "annotation" / "kappa.json"


def check(cases: list[Case], variants: list[Variant], stress: list[Variant]) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    schema, passages, cfg = load_schema(), load_passages(), load_config()
    splits = load_splits()
    split_of = {cid: name for name in ("train", "val", "test") for cid in splits[name]}
    case_ids = [c.case_id for c in cases]

    if len(set(case_ids)) != len(case_ids):
        errors.append("duplicate case ids")
    if set(split_of) != set(case_ids):
        errors.append("splits do not cover exactly the cases")
    for name in ("train", "val", "test"):
        for other in ("train", "val", "test"):
            if name < other and set(splits[name]) & set(splits[other]):
                errors.append(f"case in both {name} and {other}")

    for c in cases:
        where = c.case_id
        if set(c.attributes) != set(schema.attributes):
            errors.append(f"{where}: attributes do not match the schema")
        for a, v in c.attributes.items():
            if a in schema.attributes and v not in schema.attributes[a].values:
                errors.append(f"{where}: {a}={v} not allowed")
        if set(c.known_attributes) | set(c.unknown_attributes) != set(schema.attributes) or \
                set(c.known_attributes) & set(c.unknown_attributes):
            errors.append(f"{where}: known/unknown attributes do not partition the schema")
        if c.source_passage_id not in passages:
            errors.append(f"{where}: unknown source passage {c.source_passage_id}")
        expect_refer = not schema.faults[c.fault].user_safe or bool(c.confusable_faults)
        if (c.gold_action == REFER) != expect_refer or (c.gold_action not in (REFER, c.fault)):
            errors.append(f"{where}: gold action {c.gold_action} inconsistent")
        if c.attributes["cooling_type"] == "direct_cool" and \
                {c.attributes["condenser_fan_running"], c.attributes["evaporator_fan_running"]} != {"not_applicable"}:
            errors.append(f"{where}: direct-cool unit with fans")
        if c.attributes["power_supply_ok"] == "no" and c.attributes["compressor_running"] != "no":
            errors.append(f"{where}: compressor running without power")

    by_case = Counter(v.case_id for v in variants)
    variant_ids = [v.variant_id for v in variants + stress]
    if len(set(variant_ids)) != len(variant_ids):
        errors.append("duplicate variant ids")
    for v in variants + stress:
        if v.case_id not in split_of:
            errors.append(f"{v.variant_id}: unknown case")
            continue
        if v.lang_pair != LANG_PAIR[v.condition]:
            errors.append(f"{v.variant_id}: lang_pair {v.lang_pair} does not match {v.condition}")
        if not set(v.mentioned_attributes) <= set(schema.attributes) or "primary_symptom" not in v.mentioned_attributes:
            errors.append(f"{v.variant_id}: bad mentioned attributes")
        if v.condition.endswith("_hi") and split_of[v.case_id] not in cfg["variants"]["hindi_splits"]:
            errors.append(f"{v.variant_id}: Hindi variant outside {cfg['variants']['hindi_splits']}")
    for cid in case_ids:
        conds = {v.condition for v in variants if v.case_id == cid}
        if not {"clean", "spelling", "incomplete"} <= conds:
            errors.append(f"{cid}: missing base conditions")
    if any(split_of.get(v.case_id) != "test" for v in stress):
        errors.append("stress variants must come from the test split")

    # Duplicates: identical text for different cases in the same condition is
    # expected for very short omissions; report it, do not fail.
    seen: dict[tuple[str, str], str] = {}
    dup = 0
    for v in variants:
        key = (v.condition, v.text.lower())
        if key in seen and seen[key] != v.case_id:
            dup += 1
        seen.setdefault(key, v.case_id)
    notes.append(f"{dup} variant texts repeat across cases within a condition")
    case_dups = len(cases) - len({(tuple(sorted(c.attributes.items())), c.description) for c in cases})
    notes.append(f"{case_dups} duplicate cases (same attributes and description)")

    # Scenario provenance: quotes verbatim, passage tagged with the scenario's fault.
    fault_passages = load_fault_passages()
    for fault, scenarios in load_scenarios().items():
        for s in scenarios:
            text = passages[s["passage"]]["text"]
            if s["quote"] not in text:
                errors.append(f"scenario {s['id']}: quote not found in {s['passage']}")
            if s["passage"] not in fault_passages[fault]:
                errors.append(f"scenario {s['id']}: passage not tagged with {fault}")
    notes.append(f"variants per case: {dict(Counter(by_case.values()))}")
    return errors, notes


def kappa(path_a: Path, path_b: Path) -> dict:
    def load(p: Path) -> dict[str, dict]:
        with p.open(encoding="utf-8") as f:
            return {r["variant_id"]: r for r in csv.DictReader(f)}
    a, b = load(path_a), load(path_b)
    out = {}
    for col in [c for c in next(iter(a.values())) if c.startswith("label_")]:
        ids = [i for i in a if i in b and a[i][col].strip() and b[i][col].strip()]
        if ids:
            out[col] = {"kappa": round(cohen_kappa([a[i][col].strip().lower() for i in ids],
                                                   [b[i][col].strip().lower() for i in ids]), 4),
                        "n": len(ids)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kappa", nargs=2, type=Path, metavar=("ANNOTATOR_A_CSV", "ANNOTATOR_B_CSV"))
    args = ap.parse_args()
    if args.kappa:
        result = kappa(*args.kappa)
        KAPPA_FILE.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=1), "->", KAPPA_FILE.relative_to(BENCHMARK.parent))
        return
    cases = read_jsonl(CASES_FILE, Case)
    variants = read_jsonl(VARIANTS_FILE, Variant)
    stress = read_jsonl(STRESS_FILE, Variant)
    errors, notes = check(cases, variants, stress)
    for n in notes:
        print("note:", n)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(cases)} cases, {len(variants)} variants, {len(stress)} stress: "
          f"{'OK' if not errors else f'{len(errors)} errors'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
