"""Build the compared systems around one shared LLM, hypothesis model and retriever."""

from __future__ import annotations

from core.agent import AgentConfig
from systems.ablations import ablations
from systems.b1_direct import B1Direct
from systems.b2_llm_questions import B2LLMQuestions
from systems.b3_infogain_dx import b3
from systems.q2d import q2d

MAIN = ["b1_direct", "b2_llm_questions", "b3_infogain_dx", "q2d"]
ABLATIONS = ["q2d_minus_hl", "q2d_minus_fault_state", "q2d_minus_cost_clarity", "q2d_minus_normalisation"]
ALL = MAIN + ABLATIONS


def build_systems(names: list[str], llm, model, retriever, clarity, lambda_=None, mu=None) -> dict:
    cfg = AgentConfig.from_yaml()
    pool = {
        "b1_direct": lambda: B1Direct(llm, retriever, cfg.top_k),
        "b2_llm_questions": lambda: B2LLMQuestions(llm, retriever, cfg.T_max, cfg.top_k),
        "b3_infogain_dx": lambda: b3(llm, model, retriever),
        "q2d": lambda: q2d(llm, model, retriever, clarity, lambda_, mu),
    }
    for system in ablations(llm, model, retriever, clarity, lambda_, mu):
        pool[system.name] = (lambda s=system: s)
    unknown = set(names) - set(pool)
    if unknown:
        raise ValueError(f"unknown systems: {sorted(unknown)}")
    return {n: pool[n]() for n in names}
