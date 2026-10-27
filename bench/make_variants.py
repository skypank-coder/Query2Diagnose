"""Render every case under the input conditions of the paper plus Hindi.

    clean          the case's English description
    spelling       clean + spelling noise
    incomplete     English, informative attributes omitted
    codemixed_kn   Romanized Kannada-English (all splits)
    codemixed_hi   Romanized Hindi-English (val + test first; configs/benchmark.yaml)
    combined_kn/hi code-mixing + spelling noise + omission

All generated variants are `synthetic`. Also writes a Kannada + Hindi + English
stress set and the annotation exports for native speakers:
    data/benchmark/annotation/export/variants_to_annotate.csv
    data/benchmark/annotation/export/kappa_sheet.csv
"""

from __future__ import annotations

import csv
import random

from bench.build_cases import load_config, load_scenarios
from bench.noise import add_typos
from bench.render import render
from core.records import (
    BENCHMARK, CASES_FILE, LANG_PAIR, STRESS_FILE, VARIANTS_FILE, Case, Variant, load_splits, read_jsonl,
    write_jsonl,
)
from core.schema import load_schema

GENERATOR = "templates-v1"
EXPORT = BENCHMARK / "annotation" / "export"
KAPPA_PER_LANG = 30


def ordered_mentions(case: Case) -> list[str]:
    head = ["device", "primary_symptom"] + (["compartment_affected"] if "compartment_affected" in case.known_attributes else [])
    return head + [a for a in case.known_attributes if a not in head]


def omit(mentions: list[str], specific: set[str], keep_other: float, rng: random.Random) -> list[str]:
    """Paper condition (iv): keep the symptom and remove one or more key
    attributes - a random non-empty subset of the scenario-specific mentions,
    other mentions with probability 1 - keep_other, the compartment half the
    time - always removing at least one."""
    core = ["device", "primary_symptom"]
    if "compartment_affected" in mentions and rng.random() < 0.5:
        core.append("compartment_affected")
    others = [a for a in mentions if a not in ("device", "primary_symptom", "compartment_affected")]
    spec = [a for a in others if a in specific]
    drop = set(rng.sample(spec, rng.randint(1, len(spec)))) if spec else set()
    kept = [a for a in others if a not in drop and (a in specific or rng.random() < keep_other)]
    result = core + kept
    if len(result) == len(mentions):          # nothing removed yet
        removable = [a for a in result if a not in ("device", "primary_symptom")]
        result.remove(rng.choice(removable))
    return result


def mixed(lang: str, p_english: float, rng: random.Random):
    """Clause-language chooser for code-mixed text; the symptom is never English."""
    return lambda a: lang if a == "primary_symptom" or rng.random() >= p_english else "en"


def make(case: Case, split: str, cfg: dict, specific: set[str]) -> list[Variant]:
    vcfg = cfg["variants"]
    rng = random.Random(f"{cfg['seed']}-{case.case_id}")
    mentions = ordered_mentions(case)
    out: list[tuple[str, str, list[str]]] = [("clean", case.description, case.known_attributes)]
    out.append(("spelling", add_typos(case.description, vcfg["typo_rate"]["spelling"], rng), case.known_attributes))

    inc = omit(mentions, specific, vcfg["incomplete_keep_other"], rng)
    out.append(("incomplete", *render(inc, case.attributes, lambda a: "en", rng)))

    for lang, splits in (("kn", vcfg["kannada_splits"]), ("hi", vcfg["hindi_splits"])):
        if split not in splits:
            continue
        out.append((f"codemixed_{lang}", *render(mentions, case.attributes, mixed(lang, vcfg["p_english_clause"], rng), rng)))
        comb = omit(mentions, specific, vcfg["incomplete_keep_other"], rng)
        text, rendered = render(comb, case.attributes, mixed(lang, vcfg["p_english_clause"], rng), rng)
        out.append((f"combined_{lang}", add_typos(text, vcfg["typo_rate"]["combined"], rng), rendered))

    schema_order = list(load_schema().attributes)
    return [Variant(
        variant_id=f"{case.case_id}-{cond}",
        case_id=case.case_id,
        condition=cond,
        lang_pair=LANG_PAIR[cond],
        text=text,
        mentioned_attributes=[a for a in schema_order if a in rendered],
        provenance="synthetic",
        generator=GENERATOR,
    ) for cond, text, rendered in out]


def make_stress(case: Case, cfg: dict) -> Variant:
    rng = random.Random(f"{cfg['seed']}-{case.case_id}-stress")
    mentions = ordered_mentions(case)
    langs = iter(rng.sample(["kn", "hi"], 2))
    first = {}

    def pick(a: str) -> str:
        if a == "primary_symptom" or len(first) < 2:   # guarantee both Indian languages appear
            first[a] = next(langs, rng.choice(["kn", "hi"]))
            return first[a]
        return rng.choice(["kn", "hi", "en"])

    text, rendered = render(mentions, case.attributes, pick, rng)
    schema_order = list(load_schema().attributes)
    return Variant(variant_id=f"{case.case_id}-mixed_kn_hi", case_id=case.case_id, condition="mixed_kn_hi",
                   lang_pair="kn-hi-en", text=text, mentioned_attributes=[a for a in schema_order if a in rendered],
                   provenance="synthetic", generator=GENERATOR, stress=True)


def export_annotation(variants: list[Variant], cases: dict[str, Case], split_of: dict[str, str], seed: int) -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    rows = [v for v in variants if v.lang_pair in ("kn-en", "hi-en")]
    with (EXPORT / "variants_to_annotate.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant_id", "case_id", "split", "condition", "lang_pair", "clean_description",
                    "generated_text", "mentioned_attributes", "corrected_text", "written_from_scratch",
                    "annotator", "notes"])
        for v in rows:
            w.writerow([v.variant_id, v.case_id, split_of[v.case_id], v.condition, v.lang_pair,
                        cases[v.case_id].description, v.text, ";".join(v.mentioned_attributes), "", "", "", ""])
    rng = random.Random(seed)
    shared = []
    for lang in ("kn-en", "hi-en"):
        pool = [v for v in rows if v.lang_pair == lang]
        shared += rng.sample(pool, min(KAPPA_PER_LANG, len(pool)))
    with (EXPORT / "kappa_sheet.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant_id", "condition", "lang_pair", "text", "label_meaning_preserved",
                    "label_primary_symptom", "annotator"])
        for v in shared:
            w.writerow([v.variant_id, v.condition, v.lang_pair, v.text, "", "", ""])


def main() -> None:
    cfg = load_config()
    cases = read_jsonl(CASES_FILE, Case)
    splits = load_splits()
    split_of = {cid: name for name in ("train", "val", "test") for cid in splits[name]}
    specific = {s["id"]: set(s["attributes"]) - {"primary_symptom", "compartment_affected"}
                for scenarios in load_scenarios().values() for s in scenarios}
    variants = [v for c in cases for v in make(c, split_of[c.case_id], cfg, specific[c.scenario_id])]
    write_jsonl(VARIANTS_FILE, variants)

    rng = random.Random(cfg["seed"])
    test_cases = [c for c in cases if split_of[c.case_id] == "test"]
    stress_cases = sorted(rng.sample(test_cases, min(cfg["variants"]["stress_cases"], len(test_cases))),
                          key=lambda c: c.case_id)
    write_jsonl(STRESS_FILE, [make_stress(c, cfg) for c in stress_cases])
    export_annotation(variants, {c.case_id: c for c in cases}, split_of, cfg["seed"])

    from collections import Counter
    print(f"{len(variants)} variants -> {VARIANTS_FILE.name}:", dict(Counter(v.condition for v in variants)))
    print(f"{len(stress_cases)} stress variants -> {STRESS_FILE.name}; annotation exports -> {EXPORT.relative_to(BENCHMARK)}")


if __name__ == "__main__":
    main()
