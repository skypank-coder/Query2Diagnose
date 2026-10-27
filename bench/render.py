"""Render attribute mentions as a user message in English or Romanized
Kannada / Hindi code-mixed text, from data/benchmark/templates/*.yaml."""

from __future__ import annotations

import random
from functools import lru_cache

import yaml

from core.paths import DATA

TEMPLATES = DATA / "benchmark" / "templates"
IMPLICIT = {"device"}                      # every message is about a refrigerator
NO_CLAUSE = IMPLICIT | {"compartment_affected"}  # expressed inside the symptom clause


@lru_cache(maxsize=None)
def load_templates(lang: str) -> dict:
    return yaml.safe_load((TEMPLATES / f"{lang}.yaml").read_text(encoding="utf-8"))


def symptom_has_where(lang: str, symptom: str) -> bool:
    return any("{where}" in t for t in load_templates(lang)["phrases"]["primary_symptom"][symptom])


def _clause(lang: str, attribute: str, value: str, rng: random.Random, where: str | None) -> tuple[str, bool]:
    """Returns (text, compartment_rendered)."""
    t = load_templates(lang)
    options = t["phrases"][attribute][value]
    if attribute == "primary_symptom" and where is not None:
        with_where = [o for o in options if "{where}" in o]
        if with_where:
            return rng.choice(with_where).replace("{where}", t["where"][where]), True
    text = rng.choice(options)
    return text.replace("{where}", t["where"]["_none"]), False


def render(mentions: list[str], attributes: dict[str, str], clause_lang, rng: random.Random) -> tuple[str, list[str]]:
    """Render `mentions` (primary_symptom first). `clause_lang(attribute)` picks
    the language of each clause. Returns the text and the attributes it expresses."""
    where = attributes["compartment_affected"] if "compartment_affected" in mentions else None
    clauses: list[tuple[str, str]] = []
    rendered = [a for a in mentions if a in IMPLICIT]
    for attribute in mentions:
        if attribute in NO_CLAUSE:
            continue
        lang = clause_lang(attribute)
        text, got_where = _clause(lang, attribute, attributes[attribute], rng,
                                  where if attribute == "primary_symptom" else None)
        clauses.append((lang, text))
        rendered.append(attribute)
        if got_where:
            rendered.append("compartment_affected")
    return _join(clauses), rendered


def _join(clauses: list[tuple[str, str]]) -> str:
    if all(lang == "en" for lang, _ in clauses):
        first, rest = clauses[0][1], [c for _, c in clauses[1:]]
        text = first[0].upper() + first[1:] + "."
        if rest:
            body = rest[0] if len(rest) == 1 else ", ".join(rest[:-1]) + " and " + rest[-1]
            text += " " + body[0].upper() + body[1:] + "."
        return text
    return ", ".join(c.lower() for _, c in clauses)
