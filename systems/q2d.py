"""Query2Diagnose and the agent-based systems (B3 and the ablations reuse it
with different AgentConfig switches)."""

from __future__ import annotations

from dataclasses import dataclass

from core.agent import Agent, AgentConfig
from core.hypothesis import HypothesisModel
from core.llm import LLMClient
from core.records import Variant
from core.retrieval import Retriever
from sim.user_simulator import UserSimulator
from systems.base import SystemResult


@dataclass
class AgentSystem:
    name: str
    llm: LLMClient
    model: HypothesisModel
    retriever: Retriever
    config: AgentConfig
    clarity: dict[str, float] | None = None

    def run(self, variant: Variant, simulator: UserSimulator, seed: int) -> SystemResult:
        agent = Agent(self.llm, self.model, self.retriever, self.config, self.clarity)
        turn = agent.start(variant.text, seed=seed)
        while turn.action == "ask":
            q = turn.question
            sim = simulator.answer(q["text"], q["attribute"])
            turn = agent.reply(sim.text)
            agent.turns[-2].sim_value = sim.value
        r = agent.result
        transcript = [{**vars(t)} for t in agent.turns]
        return SystemResult(
            system=self.name, case_id=variant.case_id, variant_id=variant.variant_id, condition=variant.condition,
            lang_pair=variant.lang_pair, seed=seed, predicted=r.predicted, top_fault=r.top_fault,
            confidence=r.confidence, fault_probs=r.fault_probs, turns=r.turns, transcript=transcript,
            passage_ids=r.passage_ids, reason=r.reason,
            extras={"understanding": agent.understanding_summary(), "facts": r.facts, "retrieved": r.retrieved_ids},
        )


def q2d(llm, model, retriever, clarity, overrides: dict | None = None) -> AgentSystem:
    return AgentSystem("q2d", llm, model, retriever, AgentConfig.from_yaml(**(overrides or {})), clarity)
