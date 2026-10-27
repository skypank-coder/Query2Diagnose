"""Inter-annotator agreement: Cohen's kappa (unweighted and quadratic-weighted)."""

from __future__ import annotations

from collections import Counter

import numpy as np


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Unweighted Cohen's kappa for two raters over the same items."""
    if len(a) != len(b) or not a:
        raise ValueError("need two non-empty label lists of equal length")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def weighted_kappa(a: list[int], b: list[int], categories: list[int]) -> float:
    """Quadratic-weighted Cohen's kappa for ordinal ratings (e.g. relevance 1-5)."""
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        obs[idx[x], idx[y]] += 1
    obs /= obs.sum()
    exp = np.outer(obs.sum(axis=1), obs.sum(axis=0))
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    denom = (w * exp).sum()
    return 1.0 if denom == 0 else 1 - (w * obs).sum() / denom
