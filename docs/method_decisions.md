# Method decisions: code vs paper (Section III)

Kept in sync with `paper/query2diagnose_paper.tex` as `PAPER_SPEC.md` §10.4
asks. Each row is a place where the code is more specific than, or differs
from, what Section III says. "Open" rows need the team's approval before the
paper changes; "detail" rows are omitted from the paper for length only.

Last checked: 2026-11-01.

## Open differences

None. Section III was rewritten on 2026-11-01 to match the code (seven input
conditions, two language pairs, public sources only, model-free gold labels,
the stopping rule with the 0.01-bit floor).

## Details the paper leaves out

| Topic | Code | Where |
|---|---|---|
| Hypothesis smoothing | Each (fault, attribute) row is normalised, then smoothed: p ← (p + 1e-3) / (1 + 1e-3 · n_values); untagged values take the `possible` level | `configs/hypothesis.yaml`, `core/hypothesis.py` |
| Closed world | `unlisted` (0.05) applies only to the six symptoms whose iFixit page lists its causes; hedged sources tag the unaffected value typical as well | `docs/design_decisions.md` §5 |
| Repeated questions | An attribute that has been asked is never asked again; `device` is never asked | `core/questions.py` (`NEVER_ASKED`, `asked`) |
| Diagnostic candidates | An unknown attribute is a candidate only if its predicted answer distribution differs across faults by at least 0.05 (`discriminate_min`) | `core/questions.py`, `configs/agent.yaml` |
| Invalid samples | An understanding sample that is not valid JSON over the schema is retried twice with a new seed; clustering is exact match on the attribute dictionary | `core/understand.py` |
| Normaliser thresholds | RapidFuzz similarity 85 for Romanized forms, 80 for the schema vocabulary, 88 for general English; at most 3-word lexicon matches | `core/normalize.py` |
| Answer parsing | Rules first (not-sure phrases in three languages, negation-aware yes/no, option matching), LLM fallback (temperature 0, 60 tokens) only when no rule matches | `core/answers.py` |
| Support check | A fault is supported when a passage tagged with it in `data/sources/passage_faults.yaml` is in the top five | `core/retrieval.py` |
| Recall@k | Counts near-duplicates of the gold passage (word-set Jaccard ≥ 0.9) because iFixit repeats sections | `eval/metrics.py` |
| Ablation −H_L | K = 1 and no clarification but keeps λ, μ; with the tuned λ = μ = 0 it differs from B3 only in sharing Q2D's configuration | `systems/ablations.py` |
