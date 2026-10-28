"""Statistics: case-level bootstrap CIs and paired significance tests with Holm
correction (McNemar exact test for accuracy, Wilcoxon signed-rank for turns)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.stats import binomtest, wilcoxon


def bootstrap_ci(records: list, metric: Callable[[list], float], case_of: Callable, n: int = 1000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float, float]:
    """Point estimate and (1 - alpha) percentile CI, resampling *cases* (all
    seeds/variants of a case move together)."""
    by_case: dict = {}
    for r in records:
        by_case.setdefault(case_of(r), []).append(r)
    cases = list(by_case)
    point = metric(records)
    if len(cases) < 2:
        return point, point, point
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n):
        sample = rng.choice(len(cases), size=len(cases), replace=True)
        stats.append(metric([r for i in sample for r in by_case[cases[i]]]))
    low, high = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(low), float(high)


def mcnemar(a_correct: list[bool], b_correct: list[bool]) -> dict:
    """Exact McNemar test on paired correctness."""
    b = sum(x and not y for x, y in zip(a_correct, b_correct))
    c = sum(y and not x for x, y in zip(a_correct, b_correct))
    p = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    return {"a_only": b, "b_only": c, "p": float(p)}


def wilcoxon_paired(a: list[float], b: list[float]) -> dict:
    diffs = np.asarray(a, float) - np.asarray(b, float)
    if not np.any(diffs):
        return {"statistic": 0.0, "p": 1.0}
    res = wilcoxon(a, b, zero_method="zsplit")
    return {"statistic": float(res.statistic), "p": float(res.pvalue)}


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(items), 0.0, {}
    for i, (key, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[key] = running
    return out
