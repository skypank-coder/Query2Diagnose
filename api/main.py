"""Query2Diagnose HTTP API (FastAPI). All routes live under /api; the built
website (web/dist), if present, is served from /.

    POST /api/session                 start with a user message -> first system turn
    POST /api/session/{id}/answer     answer the pending question -> next turn or final result
    GET  /api/session/{id}/trace      full belief trace (H_L, H_D, fault probabilities, fault state per turn)
    GET  /api/systems                 systems and ablations a session can run
    GET  /api/results/latest          summary of the latest finished run (404 if none)
    GET  /api/benchmark/stats         dataset statistics and one case under every condition

    uvicorn api.main:app --port 8000      (Q2D_RETRIEVAL=tfidf for a fast, offline start)
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.agent import Agent, agent_defaults
from core.clarity import load_clarity
from core.hypothesis import load_hypothesis_model
from core.llm import BudgetExceeded, LLMClient, QuotaExhausted
from core.paths import RESULTS, ROOT
from core.records import (
    BENCHMARK, CASES_FILE, CONDITIONS, LANG_PAIR, STRESS_FILE, VARIANTS_FILE, Case, Variant, load_splits, read_jsonl,
)
from core.retrieval import Retriever
from core.schema import load_schema
from core.sources import load_passages
from eval.run_experiment import clarity_client, load_experiment
from systems.b1_direct import B1Direct
from systems.b2_llm_questions import B2LLMQuestions
from systems.registry import ALL, build_systems

DESCRIPTIONS = {
    "q2d": "Query2Diagnose: K interpretations, joint belief over (s, z), clarification + diagnostic questions by eq. (3)",
    "b1_direct": "B1: direct-answer LLM with retrieved passages, no questions",
    "b2_llm_questions": "B2: the same LLM asks follow-up questions with ordinary prompting",
    "b3_infogain_dx": "B3: information gain over faults only (one interpretation, H_L = 0, no clarification)",
    "q2d_minus_hl": "Ablation: no linguistic uncertainty (one interpretation, no clarification)",
    "q2d_minus_fault_state": "Ablation: an LLM tracks the state instead of the structured fault state",
    "q2d_minus_cost_clarity": "Ablation: lambda = mu = 0 (no effort or clarity terms)",
    "q2d_minus_normalisation": "Ablation: no Kannada / Hindi lexicon or fuzzy normalisation",
}


_RESOURCES: dict | None = None
_RESOURCES_LOCK = threading.Lock()


def resources() -> dict:
    """Model, retriever and LLM client, loaded once: the first caller loads them,
    concurrent callers wait for that load instead of starting their own."""
    global _RESOURCES
    if _RESOURCES is None:
        with _RESOURCES_LOCK:
            if _RESOURCES is None:
                _RESOURCES = _load_resources()
    return _RESOURCES


def _clear_resources() -> None:
    global _RESOURCES
    _RESOURCES = None


resources.cache_clear = _clear_resources  # same interface as functools.lru_cache, used by the tests


def _load_resources() -> dict:
    llm = LLMClient()
    retrieval = agent_defaults()["retrieval"]
    backend = os.getenv("Q2D_RETRIEVAL", retrieval["backend"])
    retriever = Retriever(backend=backend, model_name=retrieval["model"], chunk_words=retrieval["chunk_words"],
                          overlap=retrieval["overlap_words"])
    tuned_file = RESULTS / "tuning" / "best.json"
    tuned = json.loads(tuned_file.read_text(encoding="utf-8")) if tuned_file.exists() else {}
    overrides = {k: tuned[k] for k in ("lambda_", "mu") if k in tuned}
    # A(q) comes from the mock-user model in configs/experiment.yaml, as in the
    # experiments and tuning, not from the system LLM.
    clarity = load_clarity(clarity_client(load_experiment(None), llm).name) or {}
    return {"llm": llm, "model": load_hypothesis_model(), "retriever": retriever,
            "clarity": clarity, "overrides": overrides}


@dataclass
class Session:
    system: str
    lang: str
    message: str
    agent: Agent | None = None
    b2: B2LLMQuestions | None = None
    hits: list = field(default_factory=list)
    dialogue: list[tuple[str, str]] = field(default_factory=list)
    turns: list[dict] = field(default_factory=list)
    pending: dict | None = None
    done: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


SESSIONS: dict[str, Session] = {}


class StartRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    system: str = "q2d"
    lang: str = "en"


class PastAnswer(BaseModel):
    text: str = ""
    value: str | None = None


class AnswerRequest(BaseModel):
    text: str = ""
    value: str | None = None      # option chip value; skips parsing
    # The conversation so far, so the server can rebuild a session it no longer
    # holds (for example after a restart). LLM calls are cached, so a rebuild
    # replays the same dialogue.
    message: str | None = None
    system: str | None = None
    lang: str = "en"
    history: list[PastAnswer] = Field(default_factory=list)


def _hit_view(hit: dict) -> dict:
    p = load_passages().get(hit["passage_id"], {})
    return {**hit, "doc_title": p.get("doc_title"), "section": p.get("section"), "url": p.get("url"),
            "license": p.get("license"), "text": hit.get("text") or p.get("text", "")[:700]}


def _agent_turn(session: Session, turn) -> dict:
    out = {"t": turn.t, "action": turn.action, "question": turn.question, "belief": turn.belief,
           "fault_state": turn.fault_state, "candidates": turn.candidates,
           "hits": [_hit_view(h) for h in turn.hits], "decision": turn.decision}
    agent = session.agent
    if turn.t == 0 and agent.understanding_summary():
        out["understanding"] = agent.understanding_summary()
    if agent.result is not None:
        r = agent.result
        out["result"] = {"predicted": r.predicted, "top_fault": r.top_fault, "confidence": r.confidence,
                         "reason": r.reason, "facts": r.facts, "turns": r.turns,
                         "passages": [_hit_view({"passage_id": p, "score": None, "faults": []}) for p in r.passage_ids[:3]]}
    return out


def _final_from(obj: dict, session: Session, n_turns: int) -> dict:
    from systems.b1_direct import read_final
    predicted, top, conf, guidance = read_final(obj, load_schema().faults)
    return {"predicted": predicted, "top_fault": top, "confidence": conf, "reason": "llm_final",
            "guidance": guidance, "turns": n_turns,
            "passages": [_hit_view(h.to_dict()) for h in session.hits[:3]]}


def _b2_step(session: Session) -> dict:
    remaining = session.b2.T_max - len(session.dialogue)
    obj, _ = session.b2.next_action(session.message, session.dialogue, session.hits, remaining)
    t = len(session.dialogue)
    if obj["action"] == "ask":
        session.pending = {"attribute": obj.get("attribute"), "kind": "llm", "text": str(obj.get("question") or ""),
                           "options": []}
        return {"t": t, "action": "ask", "question": session.pending, "hits": [_hit_view(h.to_dict()) for h in session.hits]}
    session.done = True
    result = _final_from(obj, session, t)
    return {"t": t, "action": "answer" if result["predicted"] != "REFER" else "refer", "question": None,
            "result": result, "hits": [_hit_view(h.to_dict()) for h in session.hits]}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the hypothesis model, the retriever and the LLM client in the
    # background: the server answers at once, and the first demo message
    # finds everything loaded (or waits for the load already under way).
    if os.getenv("Q2D_WARMUP", "1") == "1":
        threading.Thread(target=resources, name="warm-up", daemon=True).start()
    yield


app = FastAPI(title="Query2Diagnose API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(QuotaExhausted)
async def _quota_exhausted(_request: Request, _exc: QuotaExhausted) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": (
        "The language model's free quota is used up for now. The instant examples still work; "
        "new messages will work again when the quota resets.")})


@app.exception_handler(BudgetExceeded)
async def _budget_exceeded(_request: Request, _exc: BudgetExceeded) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "The spending limit for paid model calls was reached."})


@app.exception_handler(Exception)
async def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": (
        f"The assistant could not finish this step ({type(exc).__name__}). Please try again.")})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "ready": _RESOURCES is not None}


@app.get("/api/systems")
def systems() -> dict:
    return {"default": "q2d", "systems": [{"id": s, "description": DESCRIPTIONS[s]} for s in ["q2d"] + [x for x in ALL if x != "q2d"]],
            "llm": resources()["llm"].name}


def _open_session(message: str, system: str, lang: str) -> tuple[Session, dict]:
    res = resources()
    session = Session(system=system, lang=lang if lang in ("en", "kn", "hi") else "en", message=message)
    with session.lock:
        if system == "b1_direct":
            b1 = B1Direct(res["llm"], res["retriever"])
            r = b1.run(Variant(variant_id="demo", case_id="demo", condition="clean", lang_pair="none",
                               text=message, mentioned_attributes=[], provenance="genuine", generator="demo"),
                       None, 0)
            session.done = True
            hits = [_hit_view({"passage_id": p, "score": None, "faults": []}) for p in r.passage_ids[:3]]
            turn = {"t": 0, "action": "answer" if r.predicted != "REFER" else "refer", "question": None, "hits": hits,
                    "result": {"predicted": r.predicted, "top_fault": r.top_fault, "confidence": r.confidence,
                               "reason": "direct", "guidance": r.extras.get("guidance", ""), "turns": 0,
                               "passages": hits}}
        elif system == "b2_llm_questions":
            session.b2 = B2LLMQuestions(res["llm"], res["retriever"])
            session.hits = res["retriever"].search(message, 5)
            turn = _b2_step(session)
        else:
            built = build_systems([system], res["llm"], res["model"], res["retriever"], res["clarity"],
                                  {**res["overrides"], "lang": session.lang})[system]
            session.agent = Agent(res["llm"], res["model"], res["retriever"], built.config, built.clarity)
            turn = _agent_turn(session, session.agent.start(message))
        session.turns.append(turn)
    return session, turn


def _apply_answer(session: Session, text: str, value: str | None) -> dict:
    """Caller holds session.lock."""
    if session.done or (session.agent and session.agent.result is not None):
        raise HTTPException(409, "This conversation has already finished. Start a new one.")
    if session.agent:
        turn = _agent_turn(session, session.agent.reply(text or (value or ""), value))
    else:
        q = session.pending or {}
        session.dialogue.append((q.get("text", ""), text or value or ""))
        turn = _b2_step(session)
    session.turns.append(turn)
    return turn


@app.post("/api/session")
def start(req: StartRequest) -> dict:
    if req.system not in DESCRIPTIONS:
        raise HTTPException(400, f"unknown system {req.system}")
    session, turn = _open_session(req.message, req.system, req.lang)
    sid = uuid.uuid4().hex[:12]
    SESSIONS[sid] = session
    return {"session_id": sid, "system": req.system, "turn": turn, "fault_names": _fault_names()}


@app.post("/api/session/{sid}/answer")
def answer(sid: str, req: AnswerRequest) -> dict:
    session = SESSIONS.get(sid)
    if session is None:
        # The server no longer holds this conversation (it restarted): rebuild it
        # from the message and the answers so far, then continue.
        if not req.message or req.system not in DESCRIPTIONS:
            raise HTTPException(404, "This conversation has expired. Please start it again.")
        session, _ = _open_session(req.message, req.system, req.lang)
        with session.lock:
            for past in req.history:
                _apply_answer(session, past.text, past.value)
        SESSIONS[sid] = session
    with session.lock:
        turn = _apply_answer(session, req.text, req.value)
    return {"session_id": sid, "system": session.system, "turn": turn}


@app.get("/api/session/{sid}/trace")
def trace(sid: str) -> dict:
    session = SESSIONS.get(sid)
    if session is None:
        raise HTTPException(404, "unknown session")
    return {"session_id": sid, "system": session.system, "message": session.message, "turns": session.turns}


def _latest_run_dir():
    pointer = RESULTS / "latest.json"
    if not pointer.exists():
        raise HTTPException(404, "no finished run yet")
    run_dir = RESULTS / "runs" / json.loads(pointer.read_text(encoding="utf-8"))["run_id"]
    if not (run_dir / "summary.json").exists():
        raise HTTPException(404, "no finished run yet")
    return run_dir


@app.get("/api/results/latest")
def results_latest() -> dict:
    return json.loads((_latest_run_dir() / "summary.json").read_text(encoding="utf-8"))


@app.get("/api/results/sensitivity")
def results_sensitivity() -> list[dict]:
    """B3 and Q2D under each hypothesis weight set (finished sensitivity runs only)."""
    from eval.export_latex import side_runs
    order = ["base", "flat", "sharp", "soft_atypical", "hard_atypical"]
    runs = sorted(side_runs("weights"),
                  key=lambda s: order.index(s["hypothesis_weights"]) if s["hypothesis_weights"] in order else 99)
    return [{"weights": s["hypothesis_weights"], "run_id": s["run_id"], "seeds": s["seeds"],
             "systems": {k: s["main"][k]["all"] for k in ("b3_infogain_dx", "q2d") if k in s["main"]}} for s in runs]


EXAMPLE_VARIANT = "c0179-codemixed_kn"   # the Kannada-English dialogue replayed on the home page


@app.get("/api/results/example")
def results_example(variant_id: str = EXAMPLE_VARIANT, system: str = "q2d", seed: int = 0) -> dict:
    """One saved dialogue from the latest run, exactly as logged."""
    run_dir = _latest_run_dir()
    path = run_dir / f"{system}.jsonl"
    record = None
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["variant_id"] == variant_id and r["seed"] == seed:
                record = r
                break
    if record is None:
        raise HTTPException(404, "no such dialogue in the latest run")
    variant = next((v for v in read_jsonl(VARIANTS_FILE, Variant) if v.variant_id == variant_id), None)
    understanding = record.get("extras", {}).get("understanding") or {}
    return {
        "run_id": run_dir.name, "variant_id": variant_id, "seed": seed, "system": system,
        "message": variant.text if variant else None, "condition": variant.condition if variant else None,
        "changes": understanding.get("changes", []),
        "turns": [{"kind": (t.get("question") or {}).get("kind"), "question": (t.get("question") or {}).get("text"),
                   "answer": t.get("answer_text")} for t in record["transcript"] if t.get("action") == "ask"],
        "predicted": record["predicted"], "fault_name": _fault_names().get(record["predicted"], {}).get("name"),
        "confidence": record.get("confidence"),
        "passages": [_hit_view({"passage_id": p, "score": None, "faults": []}) for p in record.get("passage_ids", [])[:1]],
    }


@lru_cache(maxsize=1)
def _fault_names() -> dict[str, dict[str, Any]]:
    return {z: {"name": f.name, "user_safe": f.user_safe} for z, f in load_schema().faults.items()}


@app.get("/api/benchmark/stats")
def benchmark_stats() -> dict:
    cases = read_jsonl(CASES_FILE, Case)
    variants = read_jsonl(VARIANTS_FILE, Variant)
    stress = read_jsonl(STRESS_FILE, Variant)
    splits = load_splits()
    example_case = next(c for c in cases if c.case_id in splits["test"] and c.gold_action_reason == "identifiable")
    examples = [{"condition": v.condition, "lang_pair": v.lang_pair, "text": v.text,
                 "mentioned": v.mentioned_attributes} for v in variants if v.case_id == example_case.case_id]
    kappa_file = BENCHMARK / "annotation" / "kappa.json"
    return {
        "n_cases": len(cases), "n_variants": len(variants), "n_stress": len(stress),
        "splits": {k: len(splits[k]) for k in ("train", "val", "test")},
        "conditions": [{"condition": c, "lang_pair": LANG_PAIR[c], "n": sum(v.condition == c for v in variants)}
                       for c in CONDITIONS],
        "provenance": dict(Counter(v.provenance for v in variants + stress)),
        "gold_action": dict(Counter(c.gold_action_reason for c in cases)),
        "faults": [{"fault": z, **_fault_names()[z], "n": n} for z, n in Counter(c.fault for c in cases).items()],
        "example": {"case_id": example_case.case_id, "fault": example_case.fault,
                    "gold_action": example_case.gold_action, "variants": examples},
        "kappa": json.loads(kappa_file.read_text(encoding="utf-8")) if kappa_file.exists() else None,
    }


DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="site")
