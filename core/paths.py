"""Repository paths, resolved from this file so they work from any cwd."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIGS = ROOT / "configs"
RESULTS = ROOT / "results"

SCHEMA_FILE = DATA / "schema" / "fault_schema.yaml"
HYPOTHESIS_FILE = DATA / "hypothesis_model.yaml"
HYPOTHESIS_CONFIG = CONFIGS / "hypothesis.yaml"

SOURCES = DATA / "sources"
SOURCES_MANIFEST = SOURCES / "manifest.yaml"
SOURCES_RAW = SOURCES / "raw"
PASSAGES_FILE = SOURCES / "passages.jsonl"
PASSAGE_FAULTS_FILE = SOURCES / "passage_faults.yaml"
LICENSES_FILE = SOURCES / "LICENSES.md"
