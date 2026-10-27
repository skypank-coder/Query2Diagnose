"""Query2Diagnose ablations, each removing one component (paper Sec. III-H)."""

from __future__ import annotations

from core.agent import AgentConfig
from systems.q2d import AgentSystem


def ablations(llm, model, retriever, clarity, lambda_: float | None = None, mu: float | None = None) -> list[AgentSystem]:
    tuned = {k: v for k, v in (("lambda_", lambda_), ("mu", mu)) if v is not None}
    return [
        # minus linguistic uncertainty: one greedy interpretation, no clarification (keeps cost/clarity terms)
        AgentSystem("q2d_minus_hl", llm, model, retriever,
                    AgentConfig.from_yaml(K=1, allow_clarification=False, **tuned), clarity),
        # minus structured fault state: an LLM re-reads the dialogue each turn and outputs the state
        AgentSystem("q2d_minus_fault_state", llm, model, retriever,
                    AgentConfig.from_yaml(raw_state=True, **tuned), clarity),
        # minus cost and clarity terms: lambda = mu = 0
        AgentSystem("q2d_minus_cost_clarity", llm, model, retriever,
                    AgentConfig.from_yaml(lambda_=0.0, mu=0.0), clarity),
        # minus normalisation: raw text only
        AgentSystem("q2d_minus_normalisation", llm, model, retriever,
                    AgentConfig.from_yaml(use_normalization=False, **tuned), clarity),
    ]
