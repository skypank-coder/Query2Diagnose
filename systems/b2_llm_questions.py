"""B2: the same LLM asks follow-up questions with ordinary prompting and
decides itself when to stop. Same turn budget, simulator and retrieved
passages as the other systems. Each question names the schema attribute it is
about, so the rule-based simulator can answer it exactly as it answers Q2D."""

from __future__ import annotations

from dataclasses import dataclass

from core.llm import LLMClient, parse_json
from core.records import Variant
from core.retrieval import Retriever
from core.schema import load_schema
from sim.user_simulator import UserSimulator
from systems.b1_direct import SYSTEM, passages_block, read_final
from systems.base import SystemResult, fault_list


@dataclass
class B2LLMQuestions:
    llm: LLMClient
    retriever: Retriever
    T_max: int = 6
    top_k: int = 5
    name: str = "b2_llm_questions"

    def run(self, variant: Variant, simulator: UserSimulator, seed: int) -> SystemResult:
        schema = load_schema()
        hits = self.retriever.search(variant.text, self.top_k)
        facts = "\n".join(f"- {a}: {' | '.join(attr.values)}" for a, attr in schema.attributes.items() if a != "device")
        dialogue: list[tuple[str, str]] = []
        transcript: list[dict] = []
        for t in range(self.T_max + 1):
            remaining = self.T_max - t
            history = "".join(f"\nQ: {q}\nA: {a}" for q, a in dialogue)
            instruction = (
                f"You may ask at most {remaining} more question(s). Either ask ONE follow-up question about one of "
                "the observable facts, or give your final answer."
                if remaining > 0 else "You have no questions left. Give your final answer now.")
            prompt = (
                f"{fault_list(schema)}\n\nObservable facts you may ask the customer about:\n{facts}\n\n"
                f"Troubleshooting passages:\n{passages_block(hits)}\n\n"
                f'Dialogue so far:\nCustomer: """{variant.text}"""{history}\n\n{instruction}\n'
                'Reply with JSON, either {"action": "ask", "attribute": "<fact name>", "question": "<your question>"} '
                'or {"action": "final", "fault": "<fault id>", "decision": "diy" or "refer", '
                '"confidence": <0 to 1>, "guidance": "<one or two sentences>"}. '
                'If the likely fault is marked [refer], or you cannot tell, use "decision": "refer".'
            )
            reply = self.llm.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                                      temperature=0.0, seed=seed, max_tokens=200, json_mode=True, task="b2_turn")
            obj = parse_json(reply.text) or {}
            if obj.get("action") == "ask" and remaining > 0:
                question = str(obj.get("question") or "")
                sim = simulator.answer(question, obj.get("attribute"))
                dialogue.append((question, sim.text))
                transcript.append({"t": t, "action": "ask", "attribute": obj.get("attribute"), "question": question,
                                   "answer_text": sim.text, "sim_value": sim.value})
                continue
            predicted, top, conf, guidance = read_final(obj, schema.faults)
            transcript.append({"t": t, "action": "final", "raw": reply.text})
            return SystemResult(
                system=self.name, case_id=variant.case_id, variant_id=variant.variant_id,
                condition=variant.condition, lang_pair=variant.lang_pair, seed=seed, predicted=predicted,
                top_fault=top, confidence=conf, turns=len(dialogue), transcript=transcript,
                passage_ids=[h.chunk.passage_id for h in hits], reason="llm_final", extras={"guidance": guidance},
            )
        raise AssertionError("unreachable: the last iteration always returns")
