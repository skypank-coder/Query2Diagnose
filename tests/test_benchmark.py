import random

import pytest

from bench.build_cases import build, load_config, load_scenarios, possible_states
from bench.make_variants import omit
from bench.noise import add_typos
from bench.validate import check
from core.lexicon import english_vocabulary, load_entries, load_seeds
from core.records import CASES_FILE, STRESS_FILE, VARIANTS_FILE, Case, Variant, load_splits, read_jsonl
from eval.agreement import cohen_kappa, weighted_kappa


@pytest.fixture(scope="module")
def data():
    return read_jsonl(CASES_FILE, Case), read_jsonl(VARIANTS_FILE, Variant), read_jsonl(STRESS_FILE, Variant)


def test_saved_benchmark_validates(data):
    errors, _ = check(*data)
    assert errors == []


def test_build_is_deterministic(data):
    cases, _, _ = data
    assert [c.model_dump() for c in build()] == [c.model_dump() for c in cases]


def test_hindi_variants_only_in_configured_splits(data):
    _, variants, _ = data
    splits = load_splits()
    allowed = {cid for s in load_config()["variants"]["hindi_splits"] for cid in splits[s]}
    assert {v.case_id for v in variants if v.lang_pair == "hi-en"} == allowed


def test_every_scenario_state_is_its_own(data):
    # A case's attribute vector must be producible by its own scenario.
    cases, _, _ = data
    cfg, scenarios = load_config(), {s["id"]: s for ss in load_scenarios().values() for s in ss}
    for c in cases[::7]:
        assert tuple(sorted(c.attributes.items())) in possible_states(scenarios[c.scenario_id], cfg["healthy"])


def test_omission_removes_at_least_one_mention():
    rng = random.Random(0)
    mentions = ["device", "primary_symptom", "compartment_affected", "noise_type", "door_seal_condition"]
    for _ in range(200):
        kept = omit(mentions, {"noise_type"}, 1.0, rng)
        assert kept[:2] == ["device", "primary_symptom"] and len(kept) < len(mentions)
        assert "noise_type" not in kept


def test_typos_are_seeded_and_rate_zero_is_identity():
    text = "My fridge is not cooling and the compressor is running."
    assert add_typos(text, 0.5, random.Random(1)) == add_typos(text, 0.5, random.Random(1))
    assert add_typos(text, 0.0, random.Random(2)) in (text, text.lower().rstrip("."))


def test_cohen_kappa_hand_example():
    # 10 items: agree on 8 (yes,yes x5; no,no x3), disagree on 2.
    a = ["yes"] * 6 + ["no"] * 4
    b = ["yes"] * 5 + ["no"] + ["no"] * 3 + ["yes"]
    # p_o = 0.8; p_e = 0.6*0.6 + 0.4*0.4 = 0.52; kappa = 0.28/0.48
    assert cohen_kappa(a, b) == pytest.approx(0.28 / 0.48)
    assert weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1.0)


def test_lexicons_are_strings_and_seeds_avoid_english():
    english = english_vocabulary()
    for lang in ("kn", "hi"):
        hand = {f for e in load_entries(lang) for f in e["forms"]}
        for e in load_entries(lang):
            assert isinstance(e["id"], str) and isinstance(e["en"], str)
            assert all(isinstance(f, str) for f in e["forms"])
        for entry, variants in load_seeds()[lang].items():
            other = {f for e in load_entries(lang) if e["id"] != entry for f in e["forms"]}
            for v in variants:
                assert v["form"] not in english and v["form"] not in other, v
        assert hand  # hand-written forms exist
