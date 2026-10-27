"""Question selection, eq. (3):

    q_t = argmax_{q in Q_t}  E_a[ΔH_t(q, a)] - λ C(q) - μ A(q)

ΔH_t(q, a) = H(b_t) - H(b_{t+1} | q, a) is the drop in joint entropy over
(s, z); the expectation is computed exactly by enumerating every answer
(including "not sure") under the current belief. C(q) is effort normalised to
[0, 1]; A(q) is the estimated misunderstanding rate (core/clarity.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.belief import Belief, entropy
from core.questions import Question, question_cost


@dataclass
class Scored:
    question: Question
    gain: float          # E_a[ΔH] in bits
    cost: float          # C(q)
    clarity: float       # A(q)
    score: float

    def to_dict(self) -> dict:
        return {"attribute": self.question.attribute, "kind": self.question.kind, "gain": round(self.gain, 4),
                "cost": round(self.cost, 4), "clarity": round(self.clarity, 4), "score": round(self.score, 4)}


def expected_entropy_reduction(belief: Belief, attribute: str) -> float:
    h_now = belief.h
    expected_after = 0.0
    for answer in belief.answer_values(attribute):
        joint = belief.likelihood(attribute, answer) * belief.b
        p_a = joint.sum()
        if p_a > 0:
            expected_after += p_a * entropy((joint / p_a).ravel())
    return max(0.0, h_now - expected_after)


def select(belief: Belief, questions: list[Question], lambda_: float, mu: float,
           clarity: dict[str, float]) -> list[Scored]:
    """All candidates ranked by eq. (3), best first."""
    scored = []
    for q in questions:
        gain = expected_entropy_reduction(belief, q.attribute)
        cost = question_cost(belief, q.attribute)
        a = clarity.get(q.attribute, 0.0)
        scored.append(Scored(q, gain, cost, a, gain - lambda_ * cost - mu * a))
    return sorted(scored, key=lambda s: -s.score)
