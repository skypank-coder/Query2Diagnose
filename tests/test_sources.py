import json
import re

from core.paths import LICENSES_FILE, PASSAGES_FILE, SOURCES_RAW
from core.schema import load_schema
from core.sources import ALLOWED_LICENSES, load_fault_passages, load_passages


def test_passage_ids_are_unique():
    ids = [json.loads(line)["passage_id"] for line in PASSAGES_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(ids) == len(set(ids))


def test_passages_are_clean_and_licensed():
    for pid, p in load_passages().items():
        assert p["text"].strip(), pid
        assert p["url"].startswith("https://"), pid
        assert p["license"].startswith(ALLOWED_LICENSES), pid
        assert not re.search(r"\[\[|\[[a-z_]+\||\{table|\+\+", p["text"]), pid


def test_only_ifixit_and_public_domain_sources():
    # Policy: no manufacturer manuals (docs/design_decisions.md, "Data sources").
    assert {p.name for p in SOURCES_RAW.iterdir()} == {"ifixit", "public_domain"}
    for path in (SOURCES_RAW / "ifixit").glob("*.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["license"] == "CC BY-NC-SA 3.0"


def test_every_source_page_is_credited_in_licenses():
    credited = LICENSES_FILE.read_text(encoding="utf-8")
    for url in {p["url"] for p in load_passages().values()}:
        assert url in credited, url


def test_passage_fault_tags_reference_known_faults_and_passages():
    schema, passages = load_schema(), load_passages()
    tags = load_fault_passages()
    assert set(tags) == set(schema.faults)
    for fault, ids in tags.items():
        assert ids, fault
        assert set(ids) <= set(passages), fault
