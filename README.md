# Query2Diagnose

Research prototype, benchmark and website for *Query2Diagnose: Uncertainty-Aware
Interactive Troubleshooting from Noisy, Code-Mixed and Incomplete User
Descriptions* (Saatwik Kumar Yadav, Rachana Bhaskar Gowda, Priyanshu Kumar
Senapati, S Md Adil Ahmed — School of CSE, RV University, Bengaluru).

A refrigerator complaint such as `fridge cooling agalla compressor sound ide`
is read as K sampled interpretations; the system keeps a joint belief over
interpretations *s* and faults *z*, asks the clarification or diagnostic
question that maximises expected entropy reduction minus effort and clarity
penalties, grounds its answer in retrieved troubleshooting passages, and
refers to a technician when the fault is unsafe or unsupported.

Every number shown on the website or written to `paper/tables` is computed
from saved run logs. Nothing is hard-coded; without a finished run the
results pages say "not run yet".

## Repository map

| Path | Contents |
|---|---|
| `core/` | Method: LLM client, normalisation, understanding (eq. 1), belief (eq. 2), fault state, questions, selection (eq. 3), clarity A(q), retrieval, policy, agent (Algorithm 1) |
| `systems/` | B1 direct, B2 LLM questions, B3 info-gain over faults, Q2D, four ablations |
| `sim/` | Rule-based user simulator (never sees the fault label) |
| `bench/` | Source fetching, passage extraction, lexicon seeding, case and variant builders, split, validation, annotation import |
| `eval/` | Metrics, experiment runner, aggregation, statistics, LaTeX/figure export, error analysis, tuning, relevance ratings |
| `api/` | FastAPI service; serves the built website |
| `web/` | React + Vite + TypeScript + Tailwind + Recharts + KaTeX site |
| `data/` | Schema, hypothesis model, sources (iFixit, ENERGY STAR), lexicons, benchmark, question templates, A(q) estimates |
| `configs/` | Agent, benchmark, experiment, hypothesis-weight and LLM settings |
| `docs/design_decisions.md` | Every choice the paper leaves open, with its justification |
| `REPRODUCE.md`, `LIMITATIONS.md` | Exact commands behind the reported numbers; limitations to adapt for the paper |

## Setup

Python ≥ 3.11 (tested on 3.13), Node ≥ 20. On Windows use `mingw32-make` where
this README says `make`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env        # then fill in the keys below
make test                   # 80+ tests, offline (mock LLM, TF-IDF retrieval)
```

### `.env`

| Key | Meaning |
|---|---|
| `LLM_PROVIDER` | `groq`, `openai`, `anthropic`, `ollama` or `mock` (offline, tests only) |
| `LLM_MODEL` | e.g. `openai/gpt-oss-20b` on Groq. B2, B3 and Q2D always share this model |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Key for the chosen provider; `.env` is git-ignored and a test fails if a key-shaped string appears in any committed file |
| `MAX_USD_PER_RUN` | Hard stop for paid calls in one process (cached calls are free) |
| `LLM_RPM`, `LLM_TPM` | Client-side throttle; defaults suit Groq's free tier |

Every LLM call is cached on disk (`.cache/llm`) by provider, model, prompt,
temperature and seed, so reruns are free and deterministic.

## Data

```bash
make data        # fetch sources (skips pages on disk), passages, lexicon seeds, benchmark, validation
make heatmap     # sanity-check the hypothesis model (results/sanity/hypothesis_heatmap.png)
```

**Sources.** Only iFixit pages (CC BY-NC-SA 3.0) and U.S. public-domain pages
are used — no manufacturer manuals, not even locally. To add one, record its
terms in `docs/design_decisions.md`, add it to `data/sources/manifest.yaml` and
run `make sources passages test` (see `data/sources/README.md`).

**Annotating variants (Kannada and Hindi speakers).** Copy
`data/benchmark/annotation/export/variants_to_annotate.csv` to
`data/benchmark/annotation/filled/<name>.csv`, rewrite `corrected_text` the way
you would really type it (mark `written_from_scratch` = yes for fresh
writing), then `make annotations`. Two annotators fill copies of
`kappa_sheet.csv` independently; `python -I -m bench.validate --kappa A.csv B.csv`
writes Cohen's κ. Details: `data/benchmark/README.md`.

## Experiments

Every experiment command prints the estimated LLM calls, tokens, cost and (on
Groq) days of free-tier quota, and asks before running. Runs are resumable:
`python -I -m eval.run_experiment --resume <run_id>`.

| Command | What | Requests (approx.) | Groq free tier |
|---|---|---|---|
| `make pilot` | 15 test cases × 7 conditions, 4 systems + 2 free ablations, K = 4, 1 seed | ~1,050 + 220 for A(q) | ~1 day |
| `make tune` | λ, μ grid on 30 validation cases × 3 conditions | ~720 | ~1 day |
| `make experiments` | full test split (60 cases × 7 conditions + 30 stress), 8 systems, 3 seeds, K = 8 | ~24,500 | ~25 days, or ~$5.40 on a paid tier |
| `make sensitivity` | B3 and Q2D under four alternative hypothesis weight sets | ~4,000 per set before cache hits; the parses are reused from `make experiments`, so after it almost none | — |
| `make experiments` with `--profile noisy_sim` | noisy simulator (wrong / not-sure answers in the user's language) | as above | |

Outputs: `results/runs/<run_id>/<system>.jsonl` (every transcript),
`manifest.json` (git commit, config, model, date, cost) and `summary.json`
(all metrics); `results/latest.json` points to the newest finished run.

```bash
make tables            # paper/tables/*.tex and paper/figures/*.pdf from results only
make errors            # results/error_analysis.md with transcript examples
make relevance-sheet   # question sheet for two human raters (1-5)
```

Tables use IEEE `tabular` and can be `\input{}` directly into Sections IV-V.
Exports refuse runs made with the mock LLM.

## Website

```bash
make api      # http://localhost:8000  (Q2D_RETRIEVAL=tfidf for a fast offline start)
make web      # http://localhost:5173  (dev server, proxies /api)
make docker   # API + built site in one container on :8000
```

Pages: Home, Live demo (chat with live belief panel; switch B1/B2/B3/Q2D on the
same input), Benchmark, Results (reads `/api/results/latest` only), Method,
Paper. The paper PDF is read from `web/public/paper.pdf`, which is git-ignored
because the repository is public.

## Licensing

Code: MIT (`LICENSE`). Files reproducing iFixit text (`data/sources/raw/ifixit`,
`data/sources/passages.jsonl`, the benchmark and retrieval indexes) are
CC BY-NC-SA 3.0; ENERGY STAR text is public domain; seed spellings come from
Aksharantar (CC-BY / CC0) and COMI-LINGUA (CC-BY-4.0). See `NOTICE`.

This is a research prototype, not repair advice. Unsafe faults (refrigerant,
sealed system, compressor and its relays, internal electrics) are always
referred to a technician.
