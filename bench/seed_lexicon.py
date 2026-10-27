"""Seed the Romanized lexicons with attested spellings from 2022-2026 resources
(licences checked 2026-10-28, docs/design_decisions.md "Language pairs"):

- Aksharantar (Madhani et al., Findings EMNLP 2023; CC-BY / CC0): romanizations
  of each entry's native-script words (Hindi and Kannada).
- COMI-LINGUA TN (Sheth et al., Findings EMNLP 2025; CC-BY-4.0): raw Hinglish
  sentences aligned token-by-token with annotator normalisations; a raw token
  becomes a variant of a lexicon form it was normalised to.

Downloads go to .cache/seeds/ (not committed). Output: data/lexicon/seeds.json,
which core/normalize.py merges with the hand-written forms.

    python -I -m bench.seed_lexicon
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import requests
import yaml
from rapidfuzz.distance import Levenshtein

from core.lexicon import english_vocabulary
from core.paths import DATA, ROOT

CACHE = ROOT / ".cache" / "seeds"
LEXICON = DATA / "lexicon"
SEEDS_FILE = LEXICON / "seeds.json"
AKSHARANTAR = "https://huggingface.co/datasets/ai4bharat/Aksharantar/resolve/main/{lang}.zip"
COMI_TN = "https://huggingface.co/datasets/LingoIITGN/COMI-LINGUA/resolve/main/{split}.csv"
LANGS = {"kn": "kan", "hi": "hin"}
MIN_COUNT = 3        # COMI-LINGUA alignments seen fewer times are dropped
MAX_EDIT = 2         # max edit distance to a hand-written form of the same entry
MIN_LEN = 3


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=120, headers={"User-Agent": "Query2Diagnose-research/0.1"}) as r:
            r.raise_for_status()
            with path.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return path


def load_lexicon(lang: str) -> list[dict]:
    return yaml.safe_load((LEXICON / f"{lang}_en.yaml").read_text(encoding="utf-8"))["entries"]


def aksharantar_variants(lang: str, entries: list[dict]) -> dict[str, Counter]:
    native_to_entry = {n: e["id"] for e in entries for n in e.get("native", [])}
    found: dict[str, Counter] = defaultdict(Counter)
    archive = fetch(AKSHARANTAR.format(lang=LANGS[lang]), CACHE / "aksharantar" / f"{LANGS[lang]}.zip")
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            with z.open(name) as f:
                for line in f:
                    row = json.loads(line)
                    entry = native_to_entry.get(row["native word"])
                    if entry:
                        found[entry][row["english word"].lower()] += 1
    return found


def comi_variants(entries: list[dict]) -> dict[str, Counter]:
    form_to_entry = {f: e["id"] for e in entries for f in e["forms"] if " " not in f}
    found: dict[str, Counter] = defaultdict(Counter)
    tokenize = lambda s: re.findall(r"[a-z]+", s.lower())
    for split in ("TN_train", "TN_test"):
        path = fetch(COMI_TN.format(split=split), CACHE / "comi-lingua" / f"{split}.csv")
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw = tokenize(row["Sentences"])
                for key, value in row.items():
                    if not key.startswith("Annotated by"):
                        continue
                    norm = tokenize(value or "")
                    if len(norm) != len(raw):
                        continue
                    for r, n in zip(raw, norm):
                        entry = form_to_entry.get(n)
                        if entry and r != n and Levenshtein.distance(r, n) <= MAX_EDIT:
                            found[entry][r] += 1
    return found


def keep(form: str, count: int, source: str, hand_forms: set[str], other_forms: set[str],
         english: frozenset[str]) -> bool:
    """A seeded spelling must be close to a hand-written form of the same entry
    (one edit for words of four letters or fewer), long enough to be
    unambiguous, frequent enough (COMI-LINGUA alignments are noisy), not a
    hand-written form of another entry, and not an English word, which
    normalisation would corrupt."""
    if len(form) < MIN_LEN or form in english or form in other_forms:
        return False
    if source == "comi-lingua" and count < MIN_COUNT:
        return False
    singles = [h for h in hand_forms if " " not in h]
    limit = 1 if len(form) <= 4 else MAX_EDIT
    return any(Levenshtein.distance(form, h) <= limit for h in singles)


def main() -> None:
    seeds: dict = {
        "generated_by": "bench/seed_lexicon.py",
        "sources": {
            "aksharantar": "ai4bharat/Aksharantar (CC-BY manual data, CC0 mined data)",
            "comi-lingua": "LingoIITGN/COMI-LINGUA TN split (CC-BY-4.0)",
        },
        "filters": {"min_count_comi": MIN_COUNT, "max_edit_to_hand_form": MAX_EDIT, "min_len": MIN_LEN,
                    "english_guard": "core.lexicon.english_vocabulary"},
    }
    for lang in LANGS:
        entries = load_lexicon(lang)
        hand = {e["id"]: set(e["forms"]) for e in entries}
        per_source = {"aksharantar": aksharantar_variants(lang, entries)}
        if lang == "hi":
            per_source["comi-lingua"] = comi_variants(entries)
        out: dict[str, list[dict]] = defaultdict(list)
        english = english_vocabulary()
        for source, found in per_source.items():
            for entry, counts in found.items():
                for form, n in counts.most_common():
                    others = set().union(*(f for e, f in hand.items() if e != entry))
                    if not keep(form, n, source, hand[entry], others, english):
                        continue
                    out[entry].append({"form": form, "source": source, "count": n,
                                       "already_hand_listed": form in hand[entry]})
        seeds[lang] = dict(sorted(out.items()))
        new = sum(not v["already_hand_listed"] for vs in out.values() for v in vs)
        print(f"{lang}: {len(out)} entries seeded, {new} new spellings")
    SEEDS_FILE.write_text(json.dumps(seeds, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"-> {SEEDS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
