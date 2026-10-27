"""Offline stand-in for an LLM, used by tests and `LLM_PROVIDER=mock` smoke
runs. It reads the same prompts a real model gets and answers with simple,
seeded rules (template phrase matching, keyword fault guesses). Its outputs are
never valid experimental results: eval/export_latex.py refuses mock runs.
"""

from __future__ import annotations

import json
import random
import re
from functools import lru_cache

from core.paths import DATA
from core.schema import load_schema

TEMPLATES = DATA / "benchmark" / "templates"


@lru_cache(maxsize=1)
def _phrases() -> list[tuple[str, str, str]]:
    """(phrase, attribute, value) from all template languages, longest first."""
    import yaml
    out = []
    for lang in ("en", "kn", "hi"):
        t = yaml.safe_load((TEMPLATES / f"{lang}.yaml").read_text(encoding="utf-8"))
        for attr, values in t["phrases"].items():
            for value, options in values.items():
                for o in options:
                    core = re.sub(r"\{where\}", " ", o).strip().lower()
                    if len(core) >= 6:
                        out.append((core, attr, str(value)))
        for comp, phrase in t["where"].items():
            if comp != "_none" and phrase.strip():
                out.append((phrase.strip().lower(), "compartment_affected", comp))
    return sorted(out, key=lambda x: -len(x[0]))


def _extract(text: str) -> dict[str, str]:
    text = " ".join(text.lower().split())
    found: dict[str, str] = {}
    for phrase, attr, value in _phrases():
        if attr not in found and phrase in text:
            found[attr] = value
    return found


def _block(content: str, label: str) -> str:
    m = re.search(label + r'[^"]*"""(.*?)"""', content, re.S)
    return m.group(1) if m else ""


class MockLLM:
    def complete(self, messages: list[dict], *, temperature: float, seed: int, task: str) -> str:
        content = messages[-1]["content"]
        rng = random.Random(f"{seed}-{task}-{content[-200:]}")
        handler = getattr(self, f"_{task}", None)
        return handler(content, messages, temperature, rng) if handler else "{}"

    def _understand(self, content, messages, temperature, rng):
        text = _block(content, "Customer message") + " " + _block(content, "Machine gloss")
        attrs = _extract(text)
        if temperature > 0:
            for a in list(attrs):
                if rng.random() < 0.12:
                    del attrs[a]
            values = load_schema().attributes
            for a in list(attrs):
                if rng.random() < 0.05:
                    attrs[a] = rng.choice(values[a].values)
        return json.dumps({"attributes": attrs})

    def _state_tracker(self, content, messages, temperature, rng):
        return json.dumps({"attributes": _extract(content)})

    def _parse_answer(self, content, messages, temperature, rng):
        options = re.findall(r"^- (\S+): (.+)$", content, re.M)
        answer = _block(content, "Answer").lower()
        for value, label in options:
            if label.lower() in answer or value.replace("_", " ") in answer:
                return json.dumps({"value": value})
        return json.dumps({"value": "not_sure"})

    def _mock_user(self, content, messages, temperature, rng):
        m = re.search(r"The true answer is: (.+)", content)
        return m.group(1).strip() if m else "not sure"

    @staticmethod
    def _faults(content: str) -> list[str]:
        block = content.split("Fault categories", 1)[-1].split("\n\n", 1)[0]
        return re.findall(r"^- (\w+):", block, re.M)

    def _direct(self, content, messages, temperature, rng):
        faults = self._faults(content)
        attrs = _extract(content)
        guess = "power_supply" if attrs.get("power_supply_ok") == "no" else rng.choice(faults or ["REFER"])
        return json.dumps({"fault": guess, "confidence": 0.5, "guidance": "Mock guidance."})

    def _b2_turn(self, content, messages, temperature, rng):
        asked = content.count("Q:")
        if asked < 2:
            attr = ["compressor_running", "frost_on_back_wall"][asked]
            return json.dumps({"action": "ask", "attribute": attr, "question": f"Mock question about {attr}?"})
        faults = self._faults(content)
        return json.dumps({"action": "final", "fault": rng.choice(faults or ["REFER"]), "confidence": 0.6,
                           "guidance": "Mock guidance."})

    def _paraphrase(self, content, messages, temperature, rng):
        return _block(content, "Question")
