"""Build data/demo_llm_cache: the LLM responses the hosted live demo needs for
its instant examples, so they answer at once on a serverless host (and work
even before an API key is configured there).

    python -m eval.seed_demo_cache

Runs the demo dialogues of eval.export_site through the API exactly as the
serverless host does (TF-IDF retrieval), with an empty primary cache that is
seeded from .cache/llm: every response used is copied into data/demo_llm_cache.
Responses missing from .cache/llm are fetched from the configured LLM.
"""

import os
import shutil

from core.paths import DATA, ROOT

OUT = DATA / "demo_llm_cache"
shutil.rmtree(OUT, ignore_errors=True)
os.environ.update({"Q2D_RETRIEVAL": "tfidf", "Q2D_WARMUP": "0", "Q2D_CACHE_DIR": str(OUT),
                   "Q2D_SEED_CACHE": str(ROOT / ".cache" / "llm")})

from fastapi.testclient import TestClient  # noqa: E402  (after the environment is set)

import api.main as api  # noqa: E402
from core.records import CASES_FILE, VARIANTS_FILE, Case, Variant, read_jsonl  # noqa: E402
from eval.export_site import DEMOS, record  # noqa: E402


def main() -> None:
    client = TestClient(api.app)
    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    by_text = {v.text: v.case_id for v in read_jsonl(VARIANTS_FILE, Variant)}
    for demo_id, _label, message, system, case_id in DEMOS:
        case = cases[case_id or by_text[message]] if system != "b1_direct" else None
        rec = record(client, message, system, case)
        last = rec["steps"][-1]["turn"]
        result = last.get("result") or {}
        print(f"{demo_id}: {len(rec['steps']) - 1} answer(s) -> {last.get('action')} "
              f"{result.get('predicted')} (confidence {result.get('confidence')})")
    files = list(OUT.rglob("*.json"))
    print(f"{len(files)} cached responses in {OUT.relative_to(ROOT)} "
          f"({sum(f.stat().st_size for f in files) // 1024} KB)")


if __name__ == "__main__":
    main()
