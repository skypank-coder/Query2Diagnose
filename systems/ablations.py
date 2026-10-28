"""Query2Diagnose ablations, each removing one component (paper Sec. III-H)."""

from __future__ import annotations

from core.agent import AgentConfig
from systems.q2d import AgentSystem


def ablations(llm, model, retriever, clarity, overrides: dict | None = None) -> list[AgentSystem]:
    """`overrides` (run-level settings and tuned lambda / mu) apply first; each
    ablation then switches off its own component."""
    base = overrides or {}

    def cfg(**off) -> AgentConfig:
        return AgentConfig.from_yaml(**{**base, **off})

    return [
        # minus linguistic uncertainty: one greedy interpretation, no clarification (keeps cost/clarity terms)
        AgentSystem("q2d_minus_hl", llm, model, retriever, cfg(K=1, allow_clarification=False), clarity),
        # minus structured fault state: an LLM re-reads the dialogue each turn and outputs the state
        AgentSystem("q2d_minus_fault_state", llm, model, retriever, cfg(raw_state=True), clarity),
        # minus cost and clarity terms: lambda = mu = 0
        AgentSystem("q2d_minus_cost_clarity", llm, model, retriever, cfg(lambda_=0.0, mu=0.0), clarity),
        # minus normalisation: raw text only
        AgentSystem("q2d_minus_normalisation", llm, model, retriever, cfg(use_normalization=False), clarity),
    ]
