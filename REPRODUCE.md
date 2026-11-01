# Reproducing the reported numbers

Every table and figure comes from a saved run under `results/runs/<run_id>/`.
`manifest.json` in each run records the git commit, the full config, the
model, the date and the spend; `summary.json` holds every metric.

## Environment

- Python 3.13.3 (≥ 3.11 supported), CPU torch 2.14, sentence-transformers 6.2,
  faiss-cpu 1.15; Node 24 for the website.
- System LLM for every reported run: `gpt-oss:20b` (the open `gpt-oss-20b`
  weights) under Ollama on one RTX 5070 Ti Laptop GPU (12 GB) with 32 GB RAM,
  `reasoning_effort: low`, `--workers 4` with `OLLAMA_NUM_PARALLEL=4`. Cost $0.
  Llama 3.1 8B, the originally planned model, was no longer offered when the
  experiments ran (2026-10-28).
- A(q) mock users: `openai/gpt-oss-120b` on Groq, estimated once and saved in
  `data/clarity/groq-openai-gpt-oss-120b.json`; every run reuses that file.
- Retrieval: `intfloat/multilingual-e5-small` + FAISS.

## Steps

```bash
# 1. Data (deterministic; pages are pinned to their iFixit revision ids)
make data                     # sources, passages, lexicon seeds, benchmark (seed 20261028), validation
make test

# 2. Runs (set the local-GPU block of .env.example in .env; add ARGS="--workers 4"
#    or --workers 4 when the Ollama server runs with OLLAMA_NUM_PARALLEL=4)
make pilot                    # optional smoke run
make tune                     # λ, μ on validation (results/tuning/best.json)
make experiments              # full test split, 8 systems, 3 seeds, K = 8
make sensitivity              # base + four alternative hypothesis weight sets (seed 0)
make experiments ARGS="--profile noisy_sim"   # optional: noisy simulator (not run yet)

# 3. Paper tables, figures and error analysis from the finished runs
make tables                   # paper/tables/*.tex, paper/figures/*.pdf
make errors                   # results/error_analysis.md
```

Rerunning a finished configuration costs nothing: every LLM response is
cached under `.cache/llm` by (provider, model, prompt, temperature, seed).
Copy that folder along with the repository to reproduce bit-for-bit without
a GPU or API access.

## Runs behind the reported numbers

All runs: `ollama/gpt-oss:20b`, deterministic simulator, τ = 0.75, T_max = 6,
status `complete`, cost $0. Before merging, every `summary.json` was
recomputed from its `.jsonl` records and `paper/tables` regenerated from the
runs; both matched exactly.

| Run id | Profile | What | Code |
|---|---|---|---|
| `20261029T170525Z` | full grid (`results/latest.json`) | 60 test cases × 7 conditions + 30 stress = 450 variants; all 8 systems; seeds 0-2; K = 8; tuned λ = μ = 0; 10,800 dialogues. Source of `main_results`, `ablation`, `reliability`, `kn_vs_hi` and the figures | `be6c50d` |
| `20261101T061719Z-sensitivity-base` … `-hard_atypical` (5 runs) | `sensitivity` | B3 and Q2D on the same 450 variants, seed 0, under the base, flat, sharp, soft-atypical and hard-atypical weight sets. Source of `sensitivity.tex` | `ef1c832` |
| `results/tuning/` | `eval.tune` | λ, μ ∈ {0, 0.1, 0.25, 0.5, 1}² on 30 validation cases × 3 conditions, K = 8. Best: λ = μ = 0 (validation macro-F1 0.233) | `be6c50d` |
| `20261029T071216Z-pilot` | `pilot` | 15 test cases × 7 conditions; 6 systems; seed 0; K = 4; λ = μ = 0.1 (untuned). Smoke run, not a paper result | `65e587e` |

`git.dirty` is true in the full and sensitivity manifests because earlier
result files were not committed yet when those runs started; the commits
after `be6c50d` change only result files.

An earlier Groq free-tier pilot (`20261028T171154Z-pilot`) stopped at 75 / 630
records on the daily token limit. It was abandoned, is not in the repository
and is not used anywhere.
