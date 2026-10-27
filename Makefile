# On Windows run with `mingw32-make <target>`; on Linux/macOS `make <target>`.

PY ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python,$(if $(wildcard .venv/bin/python),.venv/bin/python,python))
# Isolated mode: scripts that read downloaded files must not import from cwd.
PYI = $(PY) -I

.PHONY: install sources passages data heatmap test

install:
	$(PY) -m pip install -e ".[dev]"

sources:
	$(PYI) -m bench.fetch_sources

passages:
	$(PYI) -m bench.extract_passages

data: sources passages

heatmap:
	$(PYI) -m bench.hypothesis_heatmap

test:
	$(PYI) -m pytest -q
