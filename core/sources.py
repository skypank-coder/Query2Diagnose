"""Source passages (data/sources/passages.jsonl) and their fault tags."""

from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache

import yaml

from core.paths import PASSAGE_FAULTS_FILE, PASSAGES_FILE

ALLOWED_LICENSES = ("CC BY-NC-SA 3.0", "Public domain")


@lru_cache(maxsize=1)
def load_passages() -> dict[str, dict]:
    """passage_id -> passage record."""
    with PASSAGES_FILE.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    return {r["passage_id"]: r for r in records}


@lru_cache(maxsize=1)
def load_fault_passages() -> dict[str, tuple[str, ...]]:
    """fault -> passages tagged with it (passages that can support it)."""
    raw = yaml.safe_load(PASSAGE_FAULTS_FILE.read_text(encoding="utf-8"))
    return {z: tuple(ids) for z, ids in raw.items()}


def passage_faults() -> dict[str, frozenset[str]]:
    """passage_id -> faults it supports."""
    tags: dict[str, set[str]] = defaultdict(set)
    for fault, ids in load_fault_passages().items():
        for pid in ids:
            tags[pid].add(fault)
    return {pid: frozenset(z) for pid, z in tags.items()}
