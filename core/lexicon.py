"""Romanized Kannada / Hindi lexicons (hand forms + attested seeds) and the
English domain vocabulary used to guard and correct normalisation."""

from __future__ import annotations

import json
import re
from functools import lru_cache

import yaml

from core.paths import DATA

LEXICON = DATA / "lexicon"
SEEDS_FILE = LEXICON / "seeds.json"
LANGS = ("kn", "hi")

FUNCTION_WORDS = set("""
a an the and or but if so to of in on at by for from with without into onto over under up down out off
is am are was were be been being do does did done have has had will would can could should may might must
i me my we us our you your he him his she her it its they them their this that these those there here
not no yes very too also just only all any some every each both either neither more most less least
what which who whom whose when where why how then than as because while after before again
""".split())


@lru_cache(maxsize=1)
def english_vocabulary() -> frozenset[str]:
    """Lower-cased English tokens from the source passages, the English
    templates and common function words. Used as a guard: a token in this set
    is never rewritten by the Romanized lexicons."""
    words = set(FUNCTION_WORDS)
    with (DATA / "sources" / "passages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            words |= set(re.findall(r"[a-z]+", json.loads(line)["text"].lower()))
    words |= set(re.findall(r"[a-z]+", (DATA / "benchmark" / "templates" / "en.yaml").read_text(encoding="utf-8").lower()))
    return frozenset(w for w in words if len(w) > 1)


@lru_cache(maxsize=2)
def load_entries(lang: str) -> tuple[dict, ...]:
    return tuple(yaml.safe_load((LEXICON / f"{lang}_en.yaml").read_text(encoding="utf-8"))["entries"])


@lru_cache(maxsize=1)
def load_seeds() -> dict:
    return json.loads(SEEDS_FILE.read_text(encoding="utf-8")) if SEEDS_FILE.exists() else {}


@lru_cache(maxsize=2)
def form_map(lang: str) -> dict[str, str]:
    """Romanized form (possibly multi-word) -> English, hand forms + seeds."""
    entries = {e["id"]: e for e in load_entries(lang)}
    out = {f: e["en"] for e in entries.values() for f in e["forms"]}
    for entry_id, variants in load_seeds().get(lang, {}).items():
        for v in variants:
            out.setdefault(v["form"], entries[entry_id]["en"])
    return out
