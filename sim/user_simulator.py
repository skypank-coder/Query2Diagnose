"""Rule-based user simulator (no LLM grades an LLM).

The simulator answers a question about one schema attribute from the hidden
ground-truth case: question -> attribute -> gold value -> answer text. It never
sees or reveals the fault label. Questions it cannot map to a schema
attribute get "I don't know".

Modes:
- deterministic: always truthful, English option labels;
- noisy: wrong value with `error_rate`, "not sure" with `not_sure_rate`, the
  answer phrased in the variant's language (Kannada / Hindi option labels)
  and passed through the same typo model as the benchmark.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from bench.noise import add_typos
from core.questions import templates
from core.records import Case
from core.schema import NOT_SURE, load_schema

DONT_KNOW = {"en": "I don't know", "kn": "Gottilla", "hi": "Pata nahi"}

# Ordered keyword rules: first match wins (used when a question carries no attribute).
KEYWORDS: list[tuple[str, str]] = [
    (r"error|code", "error_code"),
    (r"socket|outlet|extension|plug(ged)? (it )?in(to)? (a )?(different|another)", "works_in_other_socket"),
    (r"light|display|power", "power_supply_ok"),
    (r"frost.free|direct.cool|defrost (it )?(by hand|manually)", "cooling_type"),
    (r"where.*(sound|noise)|(sound|noise).*(where|come from|coming from)", "noise_location"),
    (r"coil", "condenser_coils_dusty"),
    (r"(fan).*(freezer|inside)|(freezer|inside).*(fan)|evaporator", "evaporator_fan_running"),
    (r"(fan).*(back|bottom|condenser)|(back|bottom).*(fan)|condenser", "condenser_fan_running"),
    (r"compressor|motor", "compressor_running"),
    (r"sound|noise|hum|click|knock|rattl|buzz", "noise_type"),
    (r"door|seal|gasket", "door_seal_condition"),
    (r"frost|ice.*wall|wall.*ice", "frost_on_back_wall"),
    (r"water|leak|puddle|drip", "water_leak_location"),
    (r"temperature|thermostat|knob|dial|setting", "thermostat_setting"),
    (r"moved|relocat|install|shift", "recent_relocation"),
    (r"stove|oven|sun|heat|clearance|ventilat|space around|against the wall", "placement_clearance"),
    (r"packed|overload|full of|vent|block", "vents_blocked_or_overloaded"),
    (r"freezer or|fridge or|which (part|compartment|section)|both", "compartment_affected"),
    (r"main problem|symptom|what.*(wrong|problem)", "primary_symptom"),
]


def question_to_attribute(text: str) -> str | None:
    t = text.lower()
    for pattern, attribute in KEYWORDS:
        if re.search(pattern, t):
            return attribute
    return None


@dataclass
class SimAnswer:
    text: str
    value: str | None          # schema value, NOT_SURE, or None (attribute not understood)
    attribute: str | None


class UserSimulator:
    def __init__(self, case: Case, mode: str = "deterministic", lang: str = "en", error_rate: float = 0.1,
                 not_sure_rate: float = 0.1, typo_rate: float = 0.1, seed: int = 0):
        self.case, self.mode, self.lang = case, mode, lang if lang in ("en", "kn", "hi") else "en"
        self.error_rate, self.not_sure_rate, self.typo_rate = error_rate, not_sure_rate, typo_rate
        self.rng = random.Random(f"{case.case_id}-{seed}-{mode}")
        self.schema = load_schema()

    def answer(self, question_text: str, attribute: str | None = None) -> SimAnswer:
        attribute = attribute if attribute in self.schema.attributes else question_to_attribute(question_text)
        if attribute is None or attribute == "device":
            return SimAnswer(DONT_KNOW[self.lang], None, None)
        value = self.case.attributes[attribute]
        if self.mode == "noisy":
            roll = self.rng.random()
            if roll < self.not_sure_rate:
                return SimAnswer(self._noisy(DONT_KNOW[self.lang]), NOT_SURE, attribute)
            if roll < self.not_sure_rate + self.error_rate:
                others = [v for v in self.schema.attributes[attribute].values if v != value]
                value = self.rng.choice(others)
        label = templates()["attributes"][attribute]["options"][value][self.lang if self.mode == "noisy" else "en"]
        text = self._noisy(label) if self.mode == "noisy" else label
        return SimAnswer(text, value, attribute)

    def _noisy(self, text: str) -> str:
        return add_typos(text, self.typo_rate, self.rng)
