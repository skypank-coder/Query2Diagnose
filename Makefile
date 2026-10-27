# On Windows run with `mingw32-make <target>`; on Linux/macOS `make <target>`.

PY ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python,$(if $(wildcard .venv/bin/python),.venv/bin/python,python))
# Isolated mode: scripts that read downloaded files must not import from cwd.
PYI = $(PY) -I

.PHONY: install sources passages seeds benchmark annotations data heatmap test

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
