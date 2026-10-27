"""Stopping rule and safety referral (paper Sec. III-F, decision 6).

- Top fault unsafe and max_z b(z) >= tau: stop and refer immediately.
- Top fault safe, >= tau and supported by a retrieved passage: stop and answer.
- Otherwise keep asking, until t = T_max or no question is worth asking; then
  answer only if the top fault is safe, >= tau and supported, else refer with
  the collected facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["ask", "answer", "refer"]


@dataclass
class Decision:
    action: Action
    fault: str | None
    confidence: float
    reason: str


def decide(top_fault: str, confidence: float, user_safe: bool, supported: bool, t: int, t_max: int,
           tau: float, can_ask: bool) -> Decision:
    confident = confidence >= tau
    if confident and not user_safe:
        return Decision("refer", top_fault, confidence, "unsafe_fault")
    if confident and supported:
        return Decision("answer", top_fault, confidence, "confident_and_supported")
    if t < t_max and can_ask:
        return Decision("ask", top_fault, confidence, "continue")
    if confident and user_safe and supported:
        return Decision("answer", top_fault, confidence, "confident_and_supported")
    if t >= t_max:
        reason = "turn_budget"
    elif not can_ask:
        reason = "no_useful_question"
    else:
        reason = "low_confidence"
    if confident and not supported:
        reason = "unsupported"
    return Decision("refer", top_fault, confidence, reason)
