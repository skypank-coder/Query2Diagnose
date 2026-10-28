"""Query2Diagnose interaction loop (paper Algorithm 1 / Fig. 2).

    Sample K interpretations of x; cluster to estimate p(s | x)
    b_0(s, z) ∝ p(z | s) p(s | x); t = 0
    while t < T_max and the stopping rule does not fire:
        Q_t = Q^c_t ∪ Q^d_t; select q_t by eq. (3); ask; parse a_t
        b_{t+1} by eq. (2); t += 1
    answer (cited passages + safe next steps) or refer (collected facts)

Step-wise API: `start(message)` and `reply(text)` each return the next Turn,
so the web API and the user simulator drive the same object. Every turn is
logged with the question, its type, the answer, H_L, H_D, joint H, top-3
faults, the fault state and the retrieval hits.

Ablation switches (AgentConfig): single interpretation (K = 1, B3),
no clarification, raw LLM state instead of the structured fault state,
lambda / mu, normalisation on / off.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any

import numpy as np
import yaml

from core.answers import parse_answer
from core.belief import Belief
from core.fault_state import build_fault_state, confirmed_facts
from core.hypothesis import HypothesisModel
from core.llm import LLMClient, parse_json
from core.paths import CONFIGS
from core.policy import Decision, decide
from core.questions import Question, candidates
from core.retrieval import Retriever, build_query, supports
from core.schema import NOT_SURE
from core.selection import select
from core.understand import Understanding, build_prompt, understand, validate


@lru_cache(maxsize=1)
def agent_defaults() -> dict:
    return yaml.safe_load((CONFIGS / "agent.yaml").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class AgentConfig:
    K: int = 8
    temperature: float = 0.7
    use_normalization: bool = True
    epsilon: float = 0.05
    eta: float = 0.05
    confirmed: float = 0.8
    unknown: float = 0.8
    lambda_: float = 0.1
    mu: float = 0.1
    min_gain_bits: float = 0.01
    discriminate_min: float = 0.05
    tau: float = 0.75
    T_max: int = 6
    top_k: int = 5
    lang: str = "en"
    allow_clarification: bool = True
    raw_state: bool = False              # ablation: LLM-tracked state instead of the structured fault state

    @classmethod
    def from_yaml(cls, **overrides: Any) -> AgentConfig:
        d = agent_defaults()
        base = cls(K=d["understanding"]["K"], temperature=d["understanding"]["temperature"],
                   use_normalization=d["understanding"]["use_normalization"],
                   epsilon=d["belief"]["epsilon"], eta=d["belief"]["eta"],
                   confirmed=d["fault_state"]["confirmed"], unknown=d["fault_state"]["unknown"],
                   lambda_=d["selection"]["lambda_"], mu=d["selection"]["mu"],
                   min_gain_bits=d["selection"]["min_gain_bits"], discriminate_min=d["selection"]["discriminate_min"],
                   tau=d["policy"]["tau"], T_max=d["policy"]["T_max"], top_k=d["retrieval"]["top_k"],
                   lang=d["questions"]["language"])
        return replace(base, **overrides)


@dataclass
class Turn:
    t: int
    action: str                          # ask | answer | refer
    question: dict | None
    belief: dict
    fault_state: dict
    candidates: list[dict]
    hits: list[dict]
    decision: dict
    answer_text: str | None = None
    answer_value: str | None = None      # what the agent parsed
    sim_value: str | None = None         # what the simulator meant (evaluation only)


@dataclass
class Result:
    predicted: str                       # fault id or REFER
    top_fault: str
    confidence: float
    fault_probs: dict[str, float]
    turns: int
    reason: str
    facts: dict[str, str]
    passage_ids: list[str]               # supporting passages first, else the retrieved ones
    retrieved_ids: list[str] = field(default_factory=list)   # final retrieval, rank order
    guidance: list[str] = field(default_factory=list)


class Agent:
    def __init__(self, llm: LLMClient, model: HypothesisModel, retriever: Retriever, config: AgentConfig,
                 clarity: dict[str, float] | None = None):
        self.llm, self.model, self.retriever, self.cfg = llm, model, retriever, config
        self.clarity = clarity or {}
        self.schema = model.schema
        self.turns: list[Turn] = []
        self.dialogue: list[tuple[str, str]] = []
        self.pending: Question | None = None
        self.result: Result | None = None
        self.asked: set[str] = set()
        self.t = 0

    # --- public step API -------------------------------------------------------
    def start(self, message: str, seed: int = 0) -> Turn:
        self.message, self.seed = message, seed
        if self.cfg.raw_state:
            self.understanding = None
            self.belief = self._raw_belief()
        else:
            self.understanding = understand(message, self.llm, k=self.cfg.K, temperature=self.cfg.temperature,
                                            seed=seed, use_normalization=self.cfg.use_normalization)
            self.belief = Belief(self.model, self.understanding.interpretations, self.understanding.probs,
                                 self.cfg.epsilon, self.cfg.eta)
        return self._step()

    def reply(self, text: str, value: str | None = None) -> Turn:
        """Answer the pending question; `value` skips parsing (UI option chips)."""
        if self.pending is None:
            raise RuntimeError("no question is pending")
        q = self.pending
        parsed = value if value is not None else parse_answer(text, q, self.llm)
        self.turns[-1].answer_text, self.turns[-1].answer_value = text, parsed
        self.dialogue.append((q.text, text))
        self.asked.add(q.attribute)
        if self.cfg.raw_state:
            self.belief = self._raw_belief()
            if parsed != NOT_SURE:
                self.belief.answers[q.attribute] = parsed
        else:
            self.belief.update(q.attribute, parsed)
        self.t += 1
        self.pending = None
        return self._step()

    # --- internals ---------------------------------------------------------------
    def _raw_belief(self) -> Belief:
        """Ablation: one LLM call reads the whole dialogue and outputs the state;
        no interpretation sampling, no explicit answer model."""
        text = self.message + "".join(f"\nQ: {q}\nA: {a}" for q, a in self.dialogue)
        messages = build_prompt(text, None)
        messages[-1]["content"] = messages[-1]["content"].replace("Customer message", "Dialogue so far")
        reply = self.llm.complete(messages, temperature=0.0, seed=self.seed, max_tokens=200, json_mode=True,
                                  task="state_tracker")
        state = validate(parse_json(reply.text), self.schema) or {}
        return Belief(self.model, [state], np.ones(1), self.cfg.epsilon, self.cfg.eta)

    def fault_state(self):
        return build_fault_state(self.schema, self.belief.interpretations, self.belief.p_s, self.belief.answers,
                                 self.cfg.confirmed, self.cfg.unknown)

    def _step(self) -> Turn:
        state = self.fault_state()
        cands = candidates(self.belief, state, self.asked, self.cfg.lang, self.cfg.discriminate_min,
                           self.cfg.allow_clarification and not self.cfg.raw_state)
        if self.cfg.raw_state:
            cands = [q for q in cands if q.attribute not in self.belief.interpretations[0]]
        ranked = select(self.belief, cands, self.cfg.lambda_, self.cfg.mu, self.clarity)
        can_ask = bool(ranked) and ranked[0].gain >= self.cfg.min_gain_bits

        top_fault, confidence = self.belief.top_faults(1)[0]
        facts = confirmed_facts(state)
        query = build_query(facts, top_fault, {z: f.name for z, f in self.schema.faults.items()})
        hits = self.retriever.search(query, self.cfg.top_k)
        decision = decide(top_fault, confidence, self.schema.faults[top_fault].user_safe,
                          supports(top_fault, hits), self.t, self.cfg.T_max, self.cfg.tau, can_ask)
        question = ranked[0].question if decision.action == "ask" else None
        turn = Turn(
            t=self.t, action=decision.action, question=question.to_dict() if question else None,
            belief={"H_L": round(self.belief.h_l, 4), "H_D": round(self.belief.h_d, 4), "H": round(self.belief.h, 4),
                    "top": [(z, round(p, 4)) for z, p in self.belief.top_faults(5)],
                    "n_interpretations": len(self.belief.interpretations)},
            fault_state={a: {"status": s.status, "value": s.value} for a, s in state.items()},
            candidates=[s.to_dict() for s in ranked[:5]],
            hits=[{**h.to_dict(), "query": query} for h in hits],
            decision=vars(decision),
        )
        self.turns.append(turn)
        if decision.action == "ask":
            self.pending = question
        else:
            self.result = self._finish(decision, facts, hits)
        return turn

    def _finish(self, decision: Decision, facts: dict[str, str], hits) -> Result:
        supporting = [h for h in hits if decision.fault in h.chunk.faults]
        guidance = [h.chunk.text for h in supporting[:2]] if decision.action == "answer" else []
        return Result(
            predicted=decision.fault if decision.action == "answer" else "REFER",
            top_fault=decision.fault,
            confidence=round(decision.confidence, 4),
            fault_probs={z: round(float(p), 4) for z, p in zip(self.model.faults, self.belief.p_z)},
            turns=self.t,
            reason=decision.reason,
            facts=facts,
            passage_ids=[h.chunk.passage_id for h in (supporting or hits)],
            retrieved_ids=[h.chunk.passage_id for h in hits],
            guidance=guidance,
        )

    def understanding_summary(self) -> dict | None:
        u: Understanding | None = self.understanding
        if u is None:
            return None
        return {"normalized": u.normalized.text if u.normalized else None,
                "changes": [vars(a) for a in u.normalized.changes] if u.normalized else [],
                "interpretations": [{"s": s, "p": round(float(p), 4)} for s, p in zip(u.interpretations, u.probs)],
                "n_valid_samples": u.n_valid, "H_L0": round(u.h_l, 4)}
