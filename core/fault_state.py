"""Structured fault state (paper Sec. III-D): per schema attribute, confirmed /
uncertain / unknown, computed from the current interpretation marginal and the
answers collected so far (decision 5: `unmentioned` is a value; confirmed if a
mentioned value has >= 0.8, unknown if `unmentioned` has >= 0.8, else uncertain).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from core.schema import NOT_SURE, UNMENTIONED, FaultSchema

Status = Literal["confirmed", "uncertain", "unknown"]


@dataclass
class AttributeState:
    status: Status
    distribution: dict[str, float]          # value (or `unmentioned`) -> mass
    value: str | None                       # confirmed value
    source: Literal["message", "answer"]


def attribute_distribution(attribute: str, interpretations: list[dict[str, str]], p_s: np.ndarray) -> dict[str, float]:
    dist: dict[str, float] = {}
    for s, p in zip(interpretations, p_s):
        v = s.get(attribute, UNMENTIONED)
        dist[v] = dist.get(v, 0.0) + float(p)
    return dist


def build_fault_state(schema: FaultSchema, interpretations: list[dict[str, str]], p_s: np.ndarray,
                      answers: dict[str, str], confirmed: float = 0.8, unknown: float = 0.8) -> dict[str, AttributeState]:
    state: dict[str, AttributeState] = {}
    for attribute in schema.attributes:
        if attribute in answers:
            a = answers[attribute]
            if a == NOT_SURE:
                state[attribute] = AttributeState("unknown", {NOT_SURE: 1.0}, None, "answer")
            else:
                state[attribute] = AttributeState("confirmed", {a: 1.0}, a, "answer")
            continue
        dist = attribute_distribution(attribute, interpretations, p_s)
        mentioned = {v: p for v, p in dist.items() if v != UNMENTIONED}
        top = max(mentioned.items(), key=lambda kv: kv[1], default=(None, 0.0))
        if top[1] >= confirmed:
            status, value = "confirmed", top[0]
        elif dist.get(UNMENTIONED, 0.0) >= unknown:
            status, value = "unknown", None
        else:
            status, value = "uncertain", None
        state[attribute] = AttributeState(status, dist, value, "message")
    return state


def confirmed_facts(state: dict[str, AttributeState]) -> dict[str, str]:
    return {a: s.value for a, s in state.items() if s.status == "confirmed" and s.value is not None}
