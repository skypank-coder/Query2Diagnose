"""B1: direct-answer LLM. One call: opening message + retrieved passages ->
fault category, refer / DIY decision, confidence, short guidance. No questions."""

from __future__ import annotations

from dataclasses import dataclass

from core.llm import LLMClient, parse_json
from core.records import Variant
from core.retrieval import Hit, Retriever
from core.schema import load_schema
from sim.user_simulator import UserSimulator
from systems.base import SystemResult, fault_list

SYSTEM = "You are a refrigerator troubleshooting assistant. Reply with one JSON object and nothing else."


def passages_block(hits: list[Hit], max_words: int = 90) -> str:
    return "\n".join(f"[{i + 1}] {' '.join(h.chunk.text.split()[:max_words])}" for i, h in enumerate(hits))


def read_final(obj: dict | None, faults: dict) -> tuple[str, str | None, float, str]:
    """(predicted, top_fault, confidence, guidance) from a final-answer JSON."""
    obj = obj or {}
    fault = obj.get("fault")
    fault = fault if fault in faults else None
    try:
        confidence = min(1.0, max(0.0, float(obj.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    decision = str(obj.get("action") or obj.get("decision") or "").lower()
    refer = decision == "refer" or fault is None or not faults[fault].user_safe
    return ("REFER" if refer else fault), fault, confidence, str(obj.get("guidance", ""))


@dataclass
class B1Direct:
    llm: LLMClient
    retriever: Retriever
    top_k: int = 5
    name: str = "b1_direct"

    def run(self, variant: Variant, simulator: UserSimulator, seed: int) -> SystemResult:
        schema = load_schema()
        hits = self.retriever.search(variant.text, self.top_k)
        prompt = (
            f"{fault_list(schema)}\n\nTroubleshooting passages:\n{passages_block(hits)}\n\n"
            f'Customer message: """{variant.text}"""\n\n'
            "Choose the single most likely fault category. If it is marked [refer], or you cannot tell with "
            'reasonable confidence, the action must be "refer".\n'
            'Reply with JSON: {"fault": "<fault id>", "action": "diy" or "refer", "confidence": <0 to 1>, '
            '"guidance": "<one or two sentences>"}'
        )
        reply = self.llm.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                                  temperature=0.0, seed=seed, max_tokens=200, json_mode=True, task="direct")
        predicted, top, conf, guidance = read_final(parse_json(reply.text), schema.faults)
        return SystemResult(
            system=self.name, case_id=variant.case_id, variant_id=variant.variant_id, condition=variant.condition,
            lang_pair=variant.lang_pair, seed=seed, predicted=predicted, top_fault=top, confidence=conf,
            turns=0, transcript=[{"t": 0, "action": "final", "raw": reply.text}],
            passage_ids=[h.chunk.passage_id for h in hits], reason="direct", extras={"guidance": guidance},
        )
