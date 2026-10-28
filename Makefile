# On Windows run with `mingw32-make <target>`; on Linux/macOS `make <target>`.

PY ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python,$(if $(wildcard .venv/bin/python),.venv/bin/python,python))
# Isolated mode: scripts that read downloaded files must not import from cwd.
PYI = $(PY) -I

.PHONY: install sources passages seeds benchmark annotations data heatmap test tune pilot experiments \n	sensitivity tables errors relevance-sheet api web all

install:
	$(PY) -m pip install -e ".[dev]"

sources:
	$(PYI) -m bench.fetch_sources

passages:
	$(PYI) -m bench.extract_passages

seeds:
	$(PYI) -m bench.seed_lexicon

benchmark:
	$(PYI) -m bench.build_cases
	$(PYI) -m bench.split
	$(PYI) -m bench.make_variants
	$(PYI) -m bench.validate

annotations:
	$(PYI) -m bench.import_annotations

data: sources passages seeds benchmark

heatmap:
	$(PYI) -m bench.hypothesis_heatmap

test:
	$(PYI) -m pytest -q

# --- experiments (Phase 5); each prints an estimate and asks before spending ---
tune:
	$(PYI) -m eval.tune

pilot:
	$(PYI) -m eval.run_experiment --profile pilot

experiments:
	$(PYI) -m eval.run_experiment

sensitivity:
	for w in flat sharp soft_atypical hard_atypical; do $(PYI) -m eval.run_experiment --profile sensitivity --weights $$w; done

tables:
	$(PYI) -m eval.export_latex

errors:
	$(PYI) -m eval.error_analysis

relevance-sheet:
	$(PYI) -m eval.relevance export
