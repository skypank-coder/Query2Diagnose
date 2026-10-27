# Query2Diagnose

Research prototype for *Query2Diagnose: Uncertainty-Aware Interactive
Troubleshooting from Noisy, Code-Mixed and Incomplete User Descriptions*
(School of CSE, RV University, Bengaluru).

Work in progress. Full setup and reproduction instructions arrive in Phase 8.

## Quick start (Phase 1)

```bash
py -3.13 -m venv .venv            # any Python >= 3.11
.venv/Scripts/python -m pip install -e ".[dev]"
mingw32-make test                 # or `make test` on Linux/macOS
mingw32-make heatmap              # sanity-check the hypothesis model
```

Licensing: code is MIT; files containing iFixit text are CC BY-NC-SA 3.0.
See [NOTICE](NOTICE).
