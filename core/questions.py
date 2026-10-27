"""Candidate questions Q_t = Q^c_t ∪ Q^d_t (paper Sec. III-E).

Clarification questions target attributes whose status is `uncertain`
(competing readings of the message); diagnostic questions target `unknown`
attributes that still discriminate between faults with non-negligible mass.
Texts come from data/questions.yaml (English, Kannada, Hindi mirrors).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

import yaml

from core.belief import Belief
from core.fault_state import AttributeState
from core.paths import DATA
from core.schema import NOT_SURE, UNMENTIONED

Kind = Literal["clarification", "diagnostic"]
NEVER_ASKED = {"device"}


@lru_cache(maxsize=1)
def templates() -> dict:
    return yaml.safe_load((DATA / "questions.yaml").read_text(encoding="utf-8"))


@dataclass
class Question:
    attribute: str
    kind: Kind
    text: str
    options: list[tuple[str, str]] = field(default_factory=list)   # (value, label)

    def to_dict(self) -> dict:
        return {"attribute": self.attribute, "kind": self.kind, "text": self.text,
                "options": [{"value": v, "label": label} for v, label in self.options]}


def render_question(attribute: str, kind: Kind, lang: str = "en", competing: list[str] | None = None) -> Question:
    t = templates()
    spec = t["attributes"][attribute]
    values = competing if competing else list(spec["options"])
    options = [(v, spec["options"][v][lang]) for v in values] + [(NOT_SURE, t["not_sure_label"][lang])]
    text = spec[lang]
    if kind == "clarification":
        text = t["clarify_prefix"][lang] + text[0].lower() + text[1:]
    return Question(attribute, kind, text, options)


def discriminates(belief: Belief, attribute: str, min_spread: float, min_mass: float = 0.01) -> bool:
    live = belief.p_z >= min_mass
    if live.sum() < 2:
        return False
    table = belief.model.table[attribute][live]
    return bool((table.max(axis=0) - table.min(axis=0)).max() >= min_spread)


def candidates(belief: Belief, state: dict[str, AttributeState], asked: set[str], lang: str = "en",
               min_spread: float = 0.05, allow_clarification: bool = True) -> list[Question]:
    out: list[Question] = []
    for attribute, st in state.items():
        if attribute in NEVER_ASKED or attribute in asked:
            continue
        if st.status == "uncertain" and allow_clarification:
            competing = [v for v, p in sorted(st.distribution.items(), key=lambda kv: -kv[1])
                         if v != UNMENTIONED and p > 0]
            out.append(render_question(attribute, "clarification", lang, competing or None))
        elif st.status == "unknown" and discriminates(belief, attribute, min_spread):
            out.append(render_question(attribute, "diagnostic", lang))
    return out


def question_cost(belief: Belief, attribute: str) -> float:
    """C(q): the attribute's effort normalised to [0, 1]."""
    return belief.model.schema.attributes[attribute].cost
