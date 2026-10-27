"""B3: information gain over fault hypotheses only (tracks H_D, no H_L).

Same pipeline as Query2Diagnose but with a single greedy interpretation (K = 1,
so p(s | x) is a point mass and H_L = 0), no clarification questions, and no
cost or clarity terms (lambda = mu = 0). With one interpretation the joint
entropy equals H_D, so eq. (3) reduces to expected information gain over faults.
"""

from __future__ import annotations

from core.agent import AgentConfig
from systems.q2d import AgentSystem


def b3(llm, model, retriever) -> AgentSystem:
    config = AgentConfig.from_yaml(K=1, allow_clarification=False, lambda_=0.0, mu=0.0)
    return AgentSystem("b3_infogain_dx", llm, model, retriever, config, clarity=None)
