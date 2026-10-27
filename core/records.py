"""Benchmark records shared by the builder, the systems and the evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from core.paths import DATA

BENCHMARK = DATA / "benchmark"
CASES_FILE = BENCHMARK / "cases.jsonl"
VARIANTS_FILE = BENCHMARK / "variants.jsonl"
STRESS_FILE = BENCHMARK / "variants_stress.jsonl"
SPLITS_FILE = BENCHMARK / "splits.json"

Provenance = Literal["genuine", "transformed", "synthetic"]
Condition = Literal["clean", "spelling", "codemixed_kn", "codemixed_hi", "incomplete",
                    "combined_kn", "combined_hi", "mixed_kn_hi"]
LangPair = Literal["kn-en", "hi-en", "none", "kn-hi-en"]

CONDITIONS: tuple[str, ...] = ("clean", "spelling", "codemixed_kn", "codemixed_hi",
                               "incomplete", "combined_kn", "combined_hi")
LANG_PAIR: dict[str, str] = {
    "clean": "none", "spelling": "none", "incomplete": "none",
    "codemixed_kn": "kn-en", "combined_kn": "kn-en",
    "codemixed_hi": "hi-en", "combined_hi": "hi-en",
    "mixed_kn_hi": "kn-hi-en",
}
NOISE_TYPE: dict[str, str] = {
    "clean": "clean", "spelling": "spelling", "incomplete": "omission",
    "codemixed_kn": "codemixing", "codemixed_hi": "codemixing",
    "combined_kn": "combined", "combined_hi": "combined", "mixed_kn_hi": "stress",
}
REFER = "REFER"


class Case(BaseModel):
    case_id: str
    scenario_id: str
    fault: str
    safety_flag: Literal["refer", "diy_ok"]
    gold_action: str                     # a user-safe fault id, or REFER
    gold_action_reason: Literal["identifiable", "unsafe_fault", "underdetermined"]
    confusable_faults: list[str]         # other faults whose scenarios yield the same full state
    oracle_posterior: float              # p(fault | all gold attributes); diagnostic only
    attributes: dict[str, str]           # full ground truth, every schema attribute
    known_attributes: list[str]          # mentioned in the clean description
    unknown_attributes: list[str]
    candidate_faults: list[str]          # p(z | known attributes) >= 0.05
    description: str                     # clean English description
    source_passage_id: str
    provenance: Provenance
    generator: str


class Variant(BaseModel):
    variant_id: str
    case_id: str
    condition: Condition
    lang_pair: LangPair
    text: str
    mentioned_attributes: list[str]
    provenance: Provenance
    generator: str
    stress: bool = False


def read_jsonl(path: Path, model: type[BaseModel]) -> list:
    with path.open(encoding="utf-8") as f:
        return [model.model_validate_json(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")


def load_splits() -> dict[str, list[str]]:
    return json.loads(SPLITS_FILE.read_text(encoding="utf-8"))
