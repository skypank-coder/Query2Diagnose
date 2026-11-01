"""Evidence retrieval (paper Sec. III-F): passages are chunked, embedded and
indexed with FAISS; the query is built from the *confirmed* attributes and the
top fault hypothesis, never from the raw user text. A retrieved chunk supports
fault z iff its passage is tagged with z in data/sources/passage_faults.yaml.

Backends: `sentence-transformers` (default intfloat/multilingual-e5-small,
with E5 "query:" / "passage:" prefixes) and `tfidf` (character n-grams; offline
tests). Embeddings are cached under .cache/retrieval.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import yaml

from core.paths import DATA, ROOT
from core.sources import load_passages, passage_faults

CACHE = ROOT / ".cache" / "retrieval"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    passage_id: str
    text: str
    faults: frozenset[str]


@dataclass
class Hit:
    chunk: Chunk
    score: float

    def to_dict(self, include_text: bool = False) -> dict:
        d = {"chunk_id": self.chunk.chunk_id, "passage_id": self.chunk.passage_id,
             "score": round(self.score, 4), "faults": sorted(self.chunk.faults)}
        return {**d, "text": self.chunk.text} if include_text else d


def build_chunks(chunk_words: int = 200, overlap: int = 40) -> list[Chunk]:
    tags = passage_faults()
    chunks = []
    for pid, p in load_passages().items():
        words = p["text"].split()
        header = f"{p['doc_title']} - {p['section']}: "
        step = max(1, chunk_words - overlap)
        starts = range(0, max(1, len(words) - overlap), step) if len(words) > chunk_words else [0]
        for k, start in enumerate(starts):
            text = header + " ".join(words[start:start + chunk_words])
            chunks.append(Chunk(f"{pid}#{k}", pid, text, tags.get(pid, frozenset())))
    return chunks


@lru_cache(maxsize=1)
def _phrases() -> dict:
    return yaml.safe_load((DATA / "benchmark" / "templates" / "en.yaml").read_text(encoding="utf-8"))["phrases"]


def build_query(confirmed: dict[str, str], top_fault: str | None, fault_names: dict[str, str]) -> str:
    """Natural-language query from confirmed facts plus the leading hypothesis."""
    parts = []
    for attribute, value in confirmed.items():
        phrases = _phrases().get(attribute, {}).get(value)
        if phrases:
            parts.append(phrases[0].replace("{where}", ""))
    if top_fault:
        parts.append(f"possible cause: {fault_names[top_fault]}")
    return ". ".join(parts) or "refrigerator problem"


class Retriever:
    def __init__(self, backend: str = "sentence-transformers", model_name: str = "intfloat/multilingual-e5-small",
                 chunk_words: int = 200, overlap: int = 40):
        self.backend, self.model_name = backend, model_name
        self._lock = threading.Lock()   # fast tokenizers must not be called from two threads at once
        self.chunks = build_chunks(chunk_words, overlap)
        texts = [c.text for c in self.chunks]
        if backend == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
            self._matrix = self._vec.fit_transform(texts)
        elif backend == "sentence-transformers":
            import faiss
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            key = hashlib.sha256(("\n".join(texts) + model_name).encode()).hexdigest()[:16]
            path = CACHE / f"{key}.npy"
            if path.exists():
                emb = np.load(path)
            else:
                emb = self._encode([f"passage: {t}" for t in texts])
                CACHE.mkdir(parents=True, exist_ok=True)
                np.save(path, emb)
            self._index = faiss.IndexFlatIP(emb.shape[1])
            self._index.add(emb)
        else:
            raise ValueError(f"unknown retrieval backend {backend}")

    def _encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True, batch_size=32), dtype="float32")

    def search(self, query: str, k: int = 5) -> list[Hit]:
        with self._lock:
            if self.backend == "tfidf":
                from sklearn.metrics.pairwise import linear_kernel
                scores = linear_kernel(self._vec.transform([query]), self._matrix).ravel()
                order = scores.argsort()[::-1][:k]
                return [Hit(self.chunks[i], float(scores[i])) for i in order]
            scores, idx = self._index.search(self._encode([f"query: {query}"]), k)
        return [Hit(self.chunks[i], float(s)) for s, i in zip(scores[0], idx[0])]


def supports(fault: str, hits: list[Hit]) -> bool:
    return any(fault in h.chunk.faults for h in hits)
