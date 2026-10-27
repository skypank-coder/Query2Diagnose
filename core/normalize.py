"""Light normalisation of noisy, code-mixed input (paper Sec. III-C).

Romanized Kannada / Hindi forms (hand lexicon + attested seeds, longest match
first, up to three words) are glossed into English; remaining unknown tokens
are matched with RapidFuzz to lexicon forms or to the English domain
vocabulary. The original text is never discarded: every token keeps an
alignment to what it became, so normalisation errors can be traced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from rapidfuzz import fuzz, process

from core.lexicon import LANGS, domain_vocabulary, english_vocabulary, form_map

MAX_PHRASE = 3


@dataclass
class Aligned:
    original: str
    normalized: str
    source: str        # keep | kn | hi | kn-fuzzy | hi-fuzzy | en-fuzzy


@dataclass
class Normalized:
    original: str
    text: str
    alignment: list[Aligned] = field(default_factory=list)

    @property
    def changes(self) -> list[Aligned]:
        return [a for a in self.alignment if a.source != "keep"]

    @property
    def language_hits(self) -> dict[str, int]:
        hits = {lang: 0 for lang in LANGS}
        for a in self.alignment:
            lang = a.source.split("-")[0]
            if lang in hits:
                hits[lang] += 1
        return hits


@lru_cache(maxsize=1)
def _single_forms() -> dict[str, list[str]]:
    return {lang: [f for f in form_map(lang) if " " not in f] for lang in LANGS}


@lru_cache(maxsize=1)
def _english_choices() -> tuple[list[str], list[str]]:
    domain = sorted(domain_vocabulary())
    general = sorted(w for w in english_vocabulary() if len(w) >= 3 and w not in domain_vocabulary())
    return domain, general


def _match_phrase(words: list[str], i: int, maps: dict[str, dict[str, str]], prefer: list[str]):
    for n in range(min(MAX_PHRASE, len(words) - i), 0, -1):
        phrase = " ".join(words[i:i + n])
        for lang in prefer:
            if phrase in maps[lang]:
                return n, maps[lang][phrase], lang
    return None


def normalize(text: str, threshold: int = 88, domain_threshold: int = 80, lexicon_threshold: int = 85) -> Normalized:
    """`domain_threshold` applies to schema / template words, `threshold` to the
    rest of the English vocabulary, `lexicon_threshold` to Romanized forms."""
    tokens = re.findall(r"[A-Za-z]+|[^A-Za-z]+", text)
    word_idx = [k for k, t in enumerate(tokens) if t[0].isalpha()]
    words = [tokens[k].lower() for k in word_idx]
    maps = {lang: form_map(lang) for lang in LANGS}
    english = english_vocabulary()

    # Language preference from unambiguous single-word hits (a form in only one lexicon).
    votes = {lang: sum(w in maps[lang] and all(w not in maps[o] for o in LANGS if o != lang)
                       for w in words) for lang in LANGS}
    prefer = sorted(LANGS, key=lambda lang: -votes[lang])

    out: list[Aligned] = []
    replaced: dict[int, tuple[int, Aligned]] = {}   # word position -> (n words, aligned)
    i = 0
    while i < len(words):
        w = words[i]
        hit = None if w in english else _match_phrase(words, i, maps, prefer)
        if hit:
            n, en, lang = hit
            original = "".join(tokens[word_idx[i]:word_idx[i + n - 1] + 1])
            replaced[i] = (n, Aligned(original, en, lang))
            i += n
            continue
        if w not in english and len(w) >= 4:
            best = None
            for lang in prefer:
                m = process.extractOne(w, _single_forms()[lang], scorer=fuzz.ratio, score_cutoff=lexicon_threshold)
                if m and (best is None or m[1] > best[1]):
                    best = (maps[lang][m[0]], m[1], f"{lang}-fuzzy")
            domain, general = _english_choices()
            for choices, cutoff in ((domain, domain_threshold), (general, threshold)):
                m = process.extractOne(w, choices, scorer=fuzz.ratio, score_cutoff=cutoff)
                if m and (best is None or m[1] > best[1]):
                    best = (m[0], m[1], "en-fuzzy")
                if best:
                    break
            if best:
                replaced[i] = (1, Aligned(tokens[word_idx[i]], best[0], best[2]))
        i += 1

    # Rebuild the text, keeping separators between untouched words.
    pieces, k, pos = [], 0, 0
    while k < len(tokens):
        if k in word_idx:
            pos = word_idx.index(k)
            if pos in replaced:
                n, aligned = replaced[pos]
                out.append(aligned)
                pieces.append(aligned.normalized)
                k = word_idx[pos + n - 1] + 1
                continue
            out.append(Aligned(tokens[k], tokens[k], "keep"))
        pieces.append(tokens[k])
        k += 1
    return Normalized(original=text, text="".join(pieces), alignment=out)
