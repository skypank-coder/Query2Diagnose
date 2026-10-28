"""Evaluation metrics (paper Sec. IV). Every function takes plain lists so it
can be unit-tested on hand-computed toy examples (tests/test_metrics.py).

Layers: understanding (slot P/R/F1), state construction (status accuracy),
question selection (informative / redundant rates, information gain per turn),
diagnosis (accuracy, macro-F1), efficiency (turns, accuracy vs turns),
reliability (ECE, Smooth ECE, Brier, abstention P/R, selective accuracy vs
coverage), safety (unsafe-advice rate), retrieval (Recall@k), robustness
(drop from clean).
"""

from __future__ import annotations

from collections import Counter

import numpy as np


# --- understanding / state ---------------------------------------------------------
def slot_prf(pred: list[set], gold: list[set]) -> dict[str, float]:
    """Micro P/R/F1 over (attribute, value) slots."""
    tp = sum(len(p & g) for p, g in zip(pred, gold))
    n_pred, n_gold = sum(len(p) for p in pred), sum(len(g) for g in gold)
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def status_accuracy(items: list[tuple[str, bool, bool]]) -> float:
    """items: (system status, gold attribute known?, confirmed value correct?).
    Correct = gold-known attribute confirmed with the right value, or
    gold-unknown attribute marked unknown; `uncertain` is never correct."""
    ok = sum((known and status == "confirmed" and value_ok) or (not known and status == "unknown")
             for status, known, value_ok in items)
    return ok / len(items) if items else 0.0


# --- diagnosis -------------------------------------------------------------------------
def accuracy(gold: list[str], pred: list[str]) -> float:
    return sum(g == p for g, p in zip(gold, pred)) / len(gold) if gold else 0.0


def macro_f1(gold: list[str], pred: list[str]) -> float:
    """Unweighted mean F1 over every label in gold ∪ pred (REFER is a label)."""
    labels = sorted(set(gold) | set(pred))
    f1s = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        fp = sum(g != label and p == label for g, p in zip(gold, pred))
        fn = sum(g == label and p != label for g, p in zip(gold, pred))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0)
    return float(np.mean(f1s)) if f1s else 0.0


# --- reliability -------------------------------------------------------------------------
def ece(confidence: list[float], correct: list[bool], bins: int = 15) -> float:
    conf, corr = np.asarray(confidence, float), np.asarray(correct, float)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for i in range(bins):
        mask = (conf > edges[i]) & (conf <= edges[i + 1]) if i else (conf >= edges[0]) & (conf <= edges[1])
        if mask.any():
            total += mask.mean() * abs(corr[mask].mean() - conf[mask].mean())
    return float(total)


def smooth_ece(confidence: list[float], correct: list[bool]) -> float:
    """Smooth ECE (Błasiok & Nakkiran, ICLR 2024) via their `relplot` package."""
    import relplot
    return float(relplot.smECE(np.asarray(confidence, float), np.asarray(correct, float)))


def brier(confidence: list[float], correct: list[bool]) -> float:
    conf, corr = np.asarray(confidence, float), np.asarray(correct, float)
    return float(np.mean((conf - corr) ** 2))


def calibration_bins(confidence: list[float], correct: list[bool], bins: int = 10) -> list[dict]:
    conf, corr = np.asarray(confidence, float), np.asarray(correct, float)
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        mask = (conf >= edges[i]) & ((conf < edges[i + 1]) if i < bins - 1 else (conf <= 1))
        if mask.any():
            out.append({"bin": i, "conf": float(conf[mask].mean()), "acc": float(corr[mask].mean()),
                        "n": int(mask.sum())})
    return out


def abstention_pr(gold_refer: list[bool], pred_refer: list[bool]) -> dict[str, float]:
    tp = sum(g and p for g, p in zip(gold_refer, pred_refer))
    n_pred, n_gold = sum(pred_refer), sum(gold_refer)
    return {"precision": tp / n_pred if n_pred else 0.0, "recall": tp / n_gold if n_gold else 0.0}


def selective_curve(confidence: list[float], correct: list[bool]) -> dict:
    """Accuracy of the most confident fraction of predictions, for every coverage;
    AURC = area under the risk-coverage curve (lower is better)."""
    order = np.argsort(-np.asarray(confidence, float), kind="stable")
    corr = np.asarray(correct, float)[order]
    n = len(corr)
    coverage = np.arange(1, n + 1) / n
    acc = np.cumsum(corr) / np.arange(1, n + 1)
    return {"coverage": coverage.tolist(), "accuracy": acc.tolist(), "aurc": float(np.mean(1 - acc)) if n else 0.0}


# --- safety ------------------------------------------------------------------------------
def unsafe_advice_rate(unsafe_case: list[bool], predicted: list[str]) -> float:
    """Share of unsafe-fault cases where the system gave DIY guidance instead of REFER."""
    rows = [p for u, p in zip(unsafe_case, predicted) if u]
    return sum(p != "REFER" for p in rows) / len(rows) if rows else 0.0


# --- retrieval ---------------------------------------------------------------------------
def recall_at_k(gold: list[set[str]], retrieved: list[list[str]], k: int) -> float:
    """`gold[i]` is the gold passage and its near-duplicates."""
    return sum(bool(set(r[:k]) & g) for g, r in zip(gold, retrieved)) / len(gold) if gold else 0.0


def near_duplicates(passages: dict[str, dict], threshold: float = 0.9) -> dict[str, set[str]]:
    """Passage -> passages whose word sets have Jaccard >= threshold (iFixit
    repeats sections verbatim across pages)."""
    words = {pid: set(p["text"].lower().split()) for pid, p in passages.items()}
    out = {pid: {pid} for pid in passages}
    ids = list(passages)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            union = words[a] | words[b]
            if union and len(words[a] & words[b]) / len(union) >= threshold:
                out[a].add(b)
                out[b].add(a)
    return out


# --- efficiency / questions ---------------------------------------------------------------
def turn_stats(turns: list[int]) -> dict[str, float]:
    arr = np.asarray(turns, float)
    return {"mean": float(arr.mean()) if len(arr) else 0.0, "median": float(np.median(arr)) if len(arr) else 0.0}


def question_rates(asked: list[list[str]], mentioned: list[set[str]], specific: list[set[str]]) -> dict[str, float]:
    """informative: asks about a fault-specific attribute (the source passage's
    attributes) not already stated; redundant: asks about a stated attribute."""
    n = informative = redundant = 0
    for qs, men, spec in zip(asked, mentioned, specific):
        for a in qs:
            n += 1
            informative += a in spec and a not in men
            redundant += a in men
    return {"n_questions": n, "informative": informative / n if n else 0.0, "redundant": redundant / n if n else 0.0}


def robustness_drop(by_condition: dict[str, float], reference: str = "clean") -> dict[str, float]:
    base = by_condition.get(reference)
    return {c: (base - v) for c, v in by_condition.items() if c != reference and base is not None}


def label_counts(values: list[str]) -> dict[str, int]:
    return dict(Counter(values))
