"""Clarity penalty A(q) in eq. (3) (decision 9; an estimate, documented as such).

For each question template and each true value of its attribute, the LLM
plays three mock users (plain English, non-technical elderly, Kannada-English
code-mixer). Each is told what they *observe* (the English phrase for that
value), not the answer, and replies to the question in their own words. The
reply is mapped back to an option by core/answers.py. A(q) is the share of
replies that do not come back as the intended value. Results are cached per
model in data/clarity/<model>.json.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import yaml

from core.answers import parse_answer
from core.llm import LLMClient
from core.paths import DATA
from core.questions import NEVER_ASKED, render_question

CLARITY_DIR = DATA / "clarity"
PERSONAS = {
    "plain": "a busy adult who is not technical and answers in plain English",
    "elderly": "an elderly person who does not know appliance part names, answers simply and sometimes guesses",
    "codemixed": "a Bengaluru resident who answers casually in Kannada-English mixed language written in Roman script",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clarity_path(model_name: str):
    return CLARITY_DIR / f"{_slug(model_name)}.json"


def _observations() -> dict[str, dict[str, str]]:
    t = yaml.safe_load((DATA / "benchmark" / "templates" / "en.yaml").read_text(encoding="utf-8"))
    return {a: {v: opts[0].replace("{where}", "") for v, opts in values.items()} for a, values in t["phrases"].items()}


def estimate_clarity(llm: LLMClient, lang: str = "en") -> dict:
    from core.schema import load_schema
    schema, observe = load_schema(), _observations()
    per_attribute, trials = {}, []
    for attribute, attr in schema.attributes.items():
        if attribute in NEVER_ASKED:
            continue
        q = render_question(attribute, "diagnostic", lang)
        wrong = total = 0
        for value in attr.values:
            for k, (persona, desc) in enumerate(PERSONAS.items()):
                prompt = (f"You are {desc}. A refrigerator technician asks you:\n\"\"\"{q.text}\"\"\"\n"
                          f"What you observe: {observe[attribute][value]}\n"
                          "Reply with one short sentence, the way this person would actually answer. "
                          "Do not mention attribute names or options.")
                reply = llm.complete([{"role": "user", "content": prompt}], temperature=0.7, seed=k,
                                     max_tokens=60, task="mock_user").text.strip()
                parsed = parse_answer(reply, q, llm)
                wrong += parsed != value
                total += 1
                trials.append({"attribute": attribute, "value": value, "persona": persona, "reply": reply,
                               "parsed": parsed})
        per_attribute[attribute] = round(wrong / total, 4)
    result = {"model": llm.name, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "method": "mock-user misunderstanding rate (core/clarity.py)", "A": per_attribute, "trials": trials}
    CLARITY_DIR.mkdir(parents=True, exist_ok=True)
    clarity_path(llm.name).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result


def load_clarity(model_name: str) -> dict[str, float] | None:
    path = clarity_path(model_name)
    return json.loads(path.read_text(encoding="utf-8"))["A"] if path.exists() else None
