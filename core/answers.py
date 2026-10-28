"""Map a free-text answer to one value of the asked attribute.

Rule-based first (normalisation, "not sure" phrases, negation-aware yes/no,
fuzzy match against option labels and the phrase templates in all three
languages); an LLM fallback is used only when the rules find nothing.
"""

from __future__ import annotations

import re
from functools import lru_cache

import yaml
from rapidfuzz import fuzz

from core.llm import LLMClient, parse_json
from core.normalize import normalize
from core.paths import DATA
from core.questions import Question
from core.schema import NOT_SURE

NOT_SURE_PHRASES = ("not sure", "don't know", "dont know", "no idea", "can't tell", "cannot tell", "unsure",
                    "pata nahi", "pata nhi", "maloom nahi", "malum nahi", "gottilla", "gotilla", "gothilla",
                    "gotthilla", "not known")
NO_WORDS = {"no", "nope", "not", "nahi", "nahin", "nhi", "nai", "illa", "ila", "silent", "dead", "never", "nothing"}
BOTH_WORDS = {"both", "dono", "donon", "eradu", "eradralloo", "eradaralloo"}
YES_WORDS = {"yes", "yeah", "yep", "yup", "haan", "han", "haa", "ha", "haudu", "houdu", "hudu", "ide", "correct",
             "running", "spinning", "works", "working", "on"}


@lru_cache(maxsize=1)
def _template_phrases() -> dict[str, list[tuple[str, str]]]:
    """attribute -> [(phrase, value)] from the benchmark phrase templates."""
    out: dict[str, list[tuple[str, str]]] = {}
    for lang in ("en", "kn", "hi"):
        t = yaml.safe_load((DATA / "benchmark" / "templates" / f"{lang}.yaml").read_text(encoding="utf-8"))
        for attr, values in t["phrases"].items():
            for value, phrases in values.items():
                for p in phrases:
                    out.setdefault(attr, []).append((p.replace("{where}", "").strip().lower(), str(value)))
    return out


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def parse_rules(text: str, question: Question) -> str | None:
    raw = text.lower().strip()
    if not raw:
        return None
    norm = normalize(text).text.lower()
    if any(p in raw or p in norm for p in NOT_SURE_PHRASES):
        return NOT_SURE
    values = [v for v, _ in question.options if v != NOT_SURE]
    if question.attribute == "compartment_affected" and "both" in values and (_words(raw) | _words(norm)) & BOTH_WORDS:
        return "both"   # otherwise the longer label "freezer" wins in "both the fridge and the freezer"

    # Exact option value or label.
    for v, label in question.options:
        if raw in (v.replace("_", " "), label.lower()):
            return v

    # Template phrases and option labels, best fuzzy match.
    candidates = [(label.lower(), v) for v, label in question.options if v != NOT_SURE]
    candidates += [(p, v) for p, v in _template_phrases().get(question.attribute, []) if v in values]
    best, best_score = None, 0.0
    for phrase, v in candidates:
        score = max(fuzz.token_set_ratio(phrase, raw), fuzz.token_set_ratio(phrase, norm))
        if phrase in raw or phrase in norm:
            score = 100 + len(phrase) / 100          # containment wins, longer phrase first
        if score > best_score:
            best, best_score = v, score
    if best is not None and best_score >= 90:
        return best

    # Yes / no attributes: negation-aware keywords.
    if "yes" in values and "no" in values:
        words = _words(raw) | _words(norm)
        if "not_applicable" in values and re.search(r"\b(no|not any|koi|illa)\b.*\bfan\b|\bfan\b.*\b(illa|nahi)\b", raw):
            return "not_applicable"
        if words & NO_WORDS:
            return "no"
        if words & YES_WORDS:
            return "yes"
    return best if best_score >= 80 else None


def parse_answer(text: str, question: Question, llm: LLMClient | None = None) -> str:
    value = parse_rules(text, question)
    if value is not None or llm is None:
        return value or NOT_SURE
    options = "\n".join(f"- {v}: {label}" for v, label in question.options)
    prompt = (f'A technician asked: """{question.text}"""\nOptions:\n{options}\n'
              f'Answer """{text}"""\n'
              'Which option does the answer mean? Reply as JSON: {"value": "<option>"}')
    reply = llm.complete([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=30, json_mode=True,
                         task="parse_answer")
    obj = parse_json(reply.text) or {}
    v = obj.get("value")
    return v if v in {o for o, _ in question.options} else NOT_SURE
