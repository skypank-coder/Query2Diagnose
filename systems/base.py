"""Shared result schema and the dialogue driver used for every system."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

from core.records import Variant
from sim.user_simulator import UserSimulator


class SystemResult(BaseModel):
    system: str
    case_id: str
    variant_id: str
    condition: str
    lang_pair: str
    seed: int
    predicted: str                      # fault id or REFER
    top_fault: str | None               # best fault guess, also when referring
    confidence: float                   # confidence in top_fault
    fault_probs: dict[str, float] | None = None
    turns: int
    transcript: list[dict[str, Any]]
    passage_ids: list[str]
    reason: str = ""
    extras: dict[str, Any] = {}


class System(Protocol):
    name: str

    def run(self, variant: Variant, simulator: UserSimulator, seed: int) -> SystemResult: ...


FAULT_LIST_HEADER = "Fault categories (id: description; [refer] = must be referred to a technician):"


def fault_list(schema) -> str:
    lines = [f"- {z}: {f.name}{'' if f.user_safe else ' [refer]'}" for z, f in schema.faults.items()]
    return FAULT_LIST_HEADER + "\n" + "\n".join(lines)
