"""Input understanding (paper Sec. III-C): sample K interpretations s of the
message x from the LLM with a strict schema prompt, validate them, and cluster
samples that agree on every schema field. Cluster frequency estimates p(s | x);
its entropy is the initial linguistic uncertainty H_L.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from core.llm import LLMClient, parse_json
from core.normalize import Normalized, normalize
from core.schema import FaultSchema, load_schema

Interpretation = dict[str, str]          # attribute -> value, mentioned attributes only

SYSTEM = ("You extract structured facts from a customer's refrigerator complaint. "
          "Reply with one JSON object and nothing else.")

EXAMPLE_IN = "my freezer is not freezing and there is a clicking sound from the back"
EXAMPLE_OUT = ('{"attributes": {"primary_symptom": "not_cooling", "compartment_affected": "freezer", '
               '"noise_type": "clicking", "noise_location": "back_bottom"}}')


@lru_cache(maxsize=1)
def schema_block() -> str:
    schema = load_schema()
    lines = [f"- {name} ({attr.description}): {' | '.join(attr.values)}"
             for name, attr in schema.attributes.items() if name != "device"]
    return "\n".join(lines)


def build_prompt(message: str, normalized: str | None) -> list[dict]:
    gloss = f'\nMachine gloss of Kannada/Hindi words and typos: """{normalized}"""' if normalized else ""
    user = (
        "Attributes and their allowed values:\n"
        f"{schema_block()}\n\n"
        "Rules:\n"
        "- Include only attributes the message states or clearly implies; leave out everything else.\n"
        "- Use exactly one listed value per attribute, spelled as listed.\n"
        "- Negations matter (\"compressor not running\" -> compressor_running: no).\n"
        "- The message may mix English with Romanized Kannada or Hindi and contain typos.\n\n"
        f'Example message: """{EXAMPLE_IN}"""\n'
        f"Example output: {EXAMPLE_OUT}\n\n"
        f'Customer message: """{message}"""{gloss}\n'
        'Output: {"attributes": {...}}'
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def validate(obj: dict | None, schema: FaultSchema) -> Interpretation | None:
    """Keep schema attributes with allowed values; reject the sample if anything
    else is malformed (paper: 'validate ... retry on invalid JSON')."""
    if not obj or not isinstance(obj.get("attributes"), dict):
        return None
    out: Interpretation = {}
    for name, value in obj["attributes"].items():
        if name not in schema.attributes or name == "device":
            continue
        if not isinstance(value, str) or value not in schema.attributes[name].values:
            return None
        out[name] = value
    return out


@dataclass
class Understanding:
    message: str
    normalized: Normalized | None
    samples: list[Interpretation | None]
    interpretations: list[Interpretation] = field(default_factory=list)
    probs: np.ndarray = field(default_factory=lambda: np.ones(1))

    @property
    def h_l(self) -> float:
        p = self.probs[self.probs > 0]
        return max(0.0, float(-(p * np.log2(p)).sum()))

    @property
    def n_valid(self) -> int:
        return sum(s is not None for s in self.samples)


def cluster(samples: list[Interpretation | None]) -> tuple[list[Interpretation], np.ndarray]:
    valid = [s for s in samples if s is not None]
    if not valid:
        return [{}], np.ones(1)
    counts = Counter(tuple(sorted(s.items())) for s in valid)
    ordered = counts.most_common()
    return [dict(k) for k, _ in ordered], np.array([c for _, c in ordered], dtype=float) / len(valid)


def understand(message: str, llm: LLMClient, k: int = 8, temperature: float = 0.7, seed: int = 0,
               use_normalization: bool = True, max_retries: int = 2) -> Understanding:
    """K samples at `temperature`; with k == 1 a single greedy parse (B3).

    The greedy parse does not depend on the run seed: it always uses LLM seed 0,
    so extra seeds re-sample only the K > 1 interpretations (docs, Sec. 5e)."""
    schema = load_schema()
    norm = normalize(message) if use_normalization else None
    gloss = norm.text if norm and norm.changes else None
    messages = build_prompt(message, gloss)
    greedy = k == 1
    temp = 0.0 if greedy else temperature
    base = 0 if greedy else seed * 1000
    samples: list[Interpretation | None] = []
    for i in range(k):
        parsed = None
        for attempt in range(max_retries + 1):
            reply = llm.complete(messages, temperature=temp, seed=base + i + 100 * attempt,
                                 max_tokens=300, json_mode=True, task="understand")
            parsed = validate(parse_json(reply.text), schema)
            if parsed is not None:
                break
        samples.append(parsed)
    interps, probs = cluster(samples)
    return Understanding(message=message, normalized=norm, samples=samples, interpretations=interps, probs=probs)
