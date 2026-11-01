"""Snapshot the website's data so it can be served by a static host (Vercel).

    python -m eval.export_site

Writes web/public/data/: summary.json, sensitivity.json, example.json,
stats.json and systems.json (the same JSON the API returns), and demo/*.json,
recordings of the rehearsed demo dialogues made through the same API the live
demo uses. Questions are answered truthfully by the benchmark's user simulator
for a matching case, by option value, exactly as in the rehearsal; with the LLM
cache from that rehearsal no API call is made. The site reads these files only
when the live API is not reachable.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api
from core.paths import ROOT
from core.records import CASES_FILE, VARIANTS_FILE, Case, Variant, read_jsonl
from sim.user_simulator import UserSimulator

OUT = ROOT / "web" / "public" / "data"
HERO = "fridge cooling agalla compressor sound ide"
FROST = "freezer alli frost jaasti aagide, compressor run aagtide, door rubber sari ide"
DEAD = "fridge bilkul band pada hai, na light hai na display"
# (id, label, message, system, case whose hidden facts answer the questions)
DEMOS = [
    ("frost-q2d", "Kannada–English · answered in two questions", FROST, "q2d", "c0179"),
    ("hero-q2d", "Kannada–English · clarifies first, then diagnoses", HERO, "q2d", "c0029"),
    ("hero-b1", "Kannada–English · plain LLM, no questions", HERO, "b1_direct", None),
    ("dead-q2d", "Hindi–English · unsafe fault, referred", DEAD, "q2d", None),
    ("dead-b1", "Hindi–English · plain LLM gives DIY advice", DEAD, "b1_direct", None),
]


def _write(name: str, obj) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


def record(client: TestClient, message: str, system: str, case: Case | None) -> dict:
    r = client.post("/api/session", json={"message": message, "system": system, "lang": "en"})
    r.raise_for_status()
    body = r.json()
    sid, turn = body["session_id"], body["turn"]
    steps = [{"turn": turn, "answer": None}]
    sim = UserSimulator(case, lang="en") if case else None
    while turn.get("action") == "ask" and sim is not None and len(steps) <= 8:
        q = turn["question"] or {}
        ans = sim.answer(q.get("text", ""), q.get("attribute"))
        steps[-1]["answer"] = {"text": ans.text, "value": ans.value}
        r = client.post(f"/api/session/{sid}/answer", json={"text": ans.text, "value": ans.value})
        r.raise_for_status()
        turn = r.json()["turn"]
        steps.append({"turn": turn, "answer": None})
    return {"message": message, "system": system, "fault_names": body["fault_names"], "steps": steps}


def main() -> None:
    client = TestClient(api.app)
    _write("summary.json", api.results_latest())
    _write("sensitivity.json", api.results_sensitivity())
    _write("example.json", api.results_example())
    _write("stats.json", api.benchmark_stats())
    systems = api.systems()
    _write("systems.json", systems)

    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    by_text = {v.text: v.case_id for v in read_jsonl(VARIANTS_FILE, Variant)}
    index = []
    for demo_id, label, message, system, case_id in DEMOS:
        case = cases[case_id or by_text[message]] if system != "b1_direct" else None
        rec = record(client, message, system, case)
        rec.update({"id": demo_id, "label": label, "llm": systems["llm"]})
        _write(f"demo/{demo_id}.json", rec)
        index.append({"id": demo_id, "label": label, "message": message, "system": system})
    _write("demo/index.json", index)


if __name__ == "__main__":
    main()
