# Reproducing the reported numbers

Every table and figure comes from a saved run under `results/runs/<run_id>/`.
`manifest.json` in each run records the git commit, the full config, the
model, the date and the spend; `summary.json` holds every metric.

## Environment

- Python 3.13.3 (≥ 3.11 supported), CPU torch 2.14, sentence-transformers 6.2,
  faiss-cpu 1.15; Node 24 for the website.
- System LLM: `openai/gpt-oss-20b` on Groq (`reasoning_effort: low`), A(q) mock
  users: `openai/gpt-oss-120b` on Groq. Llama 3.1 8B, the originally planned
  model, was no longer offered when the experiments ran (2026-10-28).
- Or locally: the same open weights as `gpt-oss:20b` under Ollama
  (`LLM_PROVIDER=ollama`, see `.env.example`). Each run's `manifest.json`
  records which provider produced it (`"llm"`); A(q) always comes from the
  saved gpt-oss-120b estimate in `data/clarity/`.
- Retrieval: `intfloat/multilingual-e5-small` + FAISS.

## Steps

```bash
# 1. Data (deterministic; pages are pinned to their iFixit revision ids)
make data                     # sources, passages, lexicon seeds, benchmark (seed 20261028), validation
make test

# 2. A(q) and the pilot run (Groq free tier)
make pilot                    # = python -I -m eval.run_experiment --profile pilot

# 3. Paper tables, figures and error analysis from the finished run
make tables                   # paper/tables/*.tex, paper/figures/*.pdf
make errors                   # results/error_analysis.md
```

Rerunning a finished configuration costs nothing: every LLM response is
cached under `.cache/llm` by (provider, model, prompt, temperature, seed).
Copy that folder along with the repository to reproduce bit-for-bit without
API access.

## Runs behind the reported numbers

| Run id | Profile | What | Status |
|---|---|---|---|
| `20261028T171154Z-pilot` | `pilot` | 15 test cases (one per fault) × 7 conditions = 105 variants; B1, B2, B3, Q2D, Q2D − H_L, Q2D − cost/clarity; seed 0; K = 4; λ = μ = 0.1 (untuned); deterministic simulator | partial: 75 / 630 records on 2026-10-28, stopped by the free tier's 200,000 tokens/day; resume with `python -I -m eval.run_experiment --resume 20261028T171154Z-pilot` |

The pilot is labelled as such on the website and in the generated tables. The
paper's main results need the full grid:

```bash
make tune                     # λ, μ on validation (results/tuning/best.json)
make experiments              # full test split, 8 systems, 3 seeds, K = 8 (~24,500 requests)
make sensitivity              # four alternative hypothesis weight sets
make experiments ARGS="--profile noisy_sim"   # optional: noisy simulator
make tables errors
```
