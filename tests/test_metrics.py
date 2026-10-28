import pytest

from eval.metrics import (
    abstention_pr, accuracy, brier, ece, macro_f1, near_duplicates, question_rates, recall_at_k,
    robustness_drop, selective_curve, slot_prf, status_accuracy, turn_stats, unsafe_advice_rate,
)
from eval.stats import bootstrap_ci, holm, mcnemar


def test_slot_prf():
    pred = [{("a", 1), ("b", 2)}, {("c", 3)}]
    gold = [{("a", 1)}, {("c", 3), ("d", 4)}]
    # tp = 2, |pred| = 3, |gold| = 3
    assert slot_prf(pred, gold) == pytest.approx({"precision": 2 / 3, "recall": 2 / 3, "f1": 2 / 3})


def test_status_accuracy():
    items = [("confirmed", True, True), ("confirmed", True, False), ("unknown", False, False),
             ("uncertain", True, True), ("uncertain", False, False)]
    assert status_accuracy(items) == pytest.approx(2 / 5)


def test_accuracy_and_macro_f1():
    gold = ["A", "A", "B", "REFER"]
    pred = ["A", "B", "B", "REFER"]
    assert accuracy(gold, pred) == 0.75
    # A: tp1 fp0 fn1 -> 2/3; B: tp1 fp1 fn0 -> 2/3; REFER: 1 -> mean 7/9
    assert macro_f1(gold, pred) == pytest.approx((2 / 3 + 2 / 3 + 1) / 3)


def test_ece_and_brier():
    conf = [0.9, 0.9, 0.1, 0.1]
    corr = [True, False, False, False]
    # bin (0.0, 0.0667]: conf .1 acc 0 -> |0-.1|*.5 ; bin .9: acc .5 -> |.5-.9|*.5 -> 0.05 + 0.2
    assert ece(conf, corr) == pytest.approx(0.25)
    assert brier(conf, corr) == pytest.approx((0.01 + 0.81 + 0.01 + 0.01) / 4)


def test_abstention_selective_and_safety():
    assert abstention_pr([True, True, False, False], [True, False, True, False]) == {"precision": 0.5, "recall": 0.5}
    curve = selective_curve([0.9, 0.8, 0.1], [True, False, True])
    assert curve["accuracy"] == pytest.approx([1.0, 0.5, 2 / 3])
    assert curve["aurc"] == pytest.approx((0 + 0.5 + 1 / 3) / 3)
    assert unsafe_advice_rate([True, True, False], ["REFER", "door_seal", "door_seal"]) == 0.5


def test_recall_at_k_with_duplicates():
    passages = {"p1": {"text": "clean the coils with a brush"}, "p2": {"text": "clean the coils with a brush"},
                "p3": {"text": "replace the door gasket"}}
    dup = near_duplicates(passages)
    assert dup["p1"] == {"p1", "p2"}
    assert recall_at_k([dup["p1"], dup["p3"]], [["p2", "p3"], ["p1", "p3"]], 1) == 0.5


def test_questions_turns_robustness():
    rates = question_rates([["x", "y"], ["z"]], [{"y"}, set()], [{"x"}, {"q"}])
    assert rates == {"n_questions": 3, "informative": 1 / 3, "redundant": 1 / 3}
    assert turn_stats([1, 2, 6]) == {"mean": 3.0, "median": 2.0}
    assert robustness_drop({"clean": 0.8, "spelling": 0.7}) == pytest.approx({"spelling": 0.1})


def test_stats():
    assert mcnemar([True, True, False, True], [False, True, False, False]) == {"a_only": 2, "b_only": 0, "p": 0.5}
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})
    point, low, high = bootstrap_ci([{"c": i, "y": i % 2} for i in range(20)],
                                    lambda rs: sum(r["y"] for r in rs) / len(rs), lambda r: r["c"], n=200)
    assert point == 0.5 and low <= 0.5 <= high
