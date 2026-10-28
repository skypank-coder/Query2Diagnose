import math

import numpy as np
import pytest

from core.answers import parse_rules
from core.belief import Belief, entropy
from core.fault_state import build_fault_state
from core.hypothesis import HypothesisConfig, HypothesisSpec, compile_model, load_hypothesis_model
from core.llm import LLMClient, Settings
from core.normalize import normalize
from core.policy import decide
from core.questions import render_question
from core.retrieval import Retriever, build_query, supports
from core.schema import NOT_SURE, FaultSchema
from core.selection import expected_entropy_reduction, select
from core.understand import cluster, understand


@pytest.fixture(scope="module")
def mock_llm(tmp_path_factory):
    import core.llm as llm_mod
    llm_mod.CACHE_DIR = tmp_path_factory.mktemp("llm-cache")
    return LLMClient(Settings.from_env(provider="mock", model="mock-1"))


@pytest.fixture(scope="module")
def tfidf():
    return Retriever(backend="tfidf")


# Toy model: two faults, one binary attribute "fan" (f1: fan off typical).
TOY = FaultSchema.model_validate({
    "version": "t", "device_scope": "toy",
    "attributes": {"fan": {"description": "d", "values": ["on", "off"], "effort": 3},
                   "noise": {"description": "d", "values": ["loud", "quiet"], "effort": 1}},
    "faults": {"f1": {"name": "F1", "user_safe": True}, "f2": {"name": "F2", "user_safe": True}},
})
TOY_CFG = HypothesisConfig.model_validate({"levels": {"typical": 1.0, "possible": 0.25, "atypical": 0.01,
                                                      "unlisted": 0.05}, "untagged": "possible", "epsilon": 0.0})


def toy_model():
    spec = HypothesisSpec.model_validate({"version": "t", "rows": {
        "f1": {"fan": {"tags": {"off": "typical"}, "cites": ["p"]}},
        "f2": {"fan": {"tags": {"on": "typical"}, "cites": ["p"]}}}})
    return compile_model(TOY, spec, TOY_CFG)   # p(off|f1) = 0.8, p(off|f2) = 0.2


def test_normalize_glosses_codemixed_and_keeps_english():
    n = normalize("fridge cooling agalla compressor sound ide")
    assert n.text == "fridge cooling not happening compressor sound is there"
    assert [a.original for a in n.alignment if a.source != "keep"] == ["agalla", "ide"]
    plain = "I can hear the compressor running and the door seal looks fine."
    assert normalize(plain).text == plain
    assert "compressor" in normalize("the compresser is runing").text


def test_cluster_estimates_p_s():
    a, b = {"x": "1"}, {"x": "2"}
    interps, probs = cluster([a, a, a, b, None])
    assert interps == [a, b] and probs.tolist() == [0.75, 0.25]


def test_belief_initialisation_eq1_and_entropies():
    m = toy_model()
    s1, s2 = {"fan": "off"}, {}
    b = Belief(m, [s1, s2], np.array([0.75, 0.25]), epsilon=0.0, eta=0.0)
    # p(z|s1) = (0.8, 0.2); p(z|s2) uniform -> b = [[0.6, 0.15], [0.125, 0.125]]
    np.testing.assert_allclose(b.b, [[0.6, 0.15], [0.125, 0.125]])
    assert b.h_l == pytest.approx(entropy(np.array([0.75, 0.25])))     # 0.8113 bits
    assert b.h_d == pytest.approx(entropy(np.array([0.725, 0.275])))
    assert b.h == pytest.approx(entropy(np.array([0.6, 0.15, 0.125, 0.125])))


def test_belief_update_eq2_by_hand():
    m = toy_model()
    b = Belief(m, [{}], np.ones(1), epsilon=0.1, eta=0.0)
    # p(a=off | z) = 0.9 p(off|z) + 0.1 (1 - p(off|z)) = (0.74, 0.26); prior uniform
    b.update("fan", "off")
    np.testing.assert_allclose(b.p_z, [0.74, 0.26])


def test_not_sure_is_uninformative():
    m = toy_model()
    b = Belief(m, [{}], np.ones(1), epsilon=0.05, eta=0.05)
    before = b.b.copy()
    b.update("fan", NOT_SURE)
    np.testing.assert_allclose(b.b, before)


def test_expected_entropy_reduction():
    m = toy_model()
    b = Belief(m, [{}], np.ones(1), epsilon=0.0, eta=0.0)
    # uninformative attribute (uniform rows) -> zero gain
    assert expected_entropy_reduction(b, "noise") == pytest.approx(0.0, abs=1e-12)
    # fan: H(z) = 1; answers off/on each w.p. 0.5, posterior (0.8, 0.2) -> H = 0.7219
    expected = 1.0 - entropy(np.array([0.8, 0.2]))
    assert expected_entropy_reduction(b, "fan") == pytest.approx(expected)


def test_clarification_gain_comes_from_linguistic_uncertainty():
    m = toy_model()
    b = Belief(m, [{"noise": "loud"}, {"noise": "quiet"}], np.array([0.5, 0.5]), epsilon=0.0, eta=0.0)
    # noise does not discriminate faults, but asking it resolves s: gain = H_L = 1 bit
    assert expected_entropy_reduction(b, "noise") == pytest.approx(1.0)


def test_selection_objective_eq3():
    m = load_hypothesis_model()
    b = Belief(m, [{"primary_symptom": "not_cooling"}], np.ones(1))
    qs = [render_question("compressor_running", "diagnostic"), render_question("condenser_coils_dusty", "diagnostic")]
    ranked = select(b, qs, lambda_=0.5, mu=1.0, clarity={"compressor_running": 0.2})
    for s in ranked:
        assert s.score == pytest.approx(s.gain - 0.5 * s.cost - 1.0 * s.clarity)
    assert ranked[0].score >= ranked[1].score


@pytest.mark.parametrize("dist, status", [
    ({"yes": 0.85, "unmentioned": 0.15}, "confirmed"),
    ({"unmentioned": 0.85, "yes": 0.15}, "unknown"),
    ({"yes": 0.5, "unmentioned": 0.5}, "uncertain"),
    ({"yes": 0.7, "no": 0.15, "unmentioned": 0.15}, "uncertain"),   # the gap case of decision 5
])
def test_fault_state_thresholds(dist, status):
    schema = load_hypothesis_model().schema
    interps, probs = [], []
    for v, p in dist.items():
        interps.append({} if v == "unmentioned" else {"compressor_running": v})
        probs.append(p)
    state = build_fault_state(schema, interps, np.array(probs), {})
    assert state["compressor_running"].status == status


def test_answers_are_negation_aware():
    q = render_question("compressor_running", "diagnostic")
    assert parse_rules("No, it is silent", q) == "no"
    assert parse_rules("the compressor is not running", q) == "no"
    assert parse_rules("haan chal raha hai", q) == "yes"
    assert parse_rules("pata nahi", q) == NOT_SURE
    where = render_question("compartment_affected", "diagnostic")
    assert parse_rules("Both the fridge and the freezer are having problems.", where) == "both"
    assert parse_rules("fridge aur freezer dono mein", where) == "both"
    assert parse_rules("only the freezer", where) == "freezer"


@pytest.mark.parametrize("args, action, reason", [
    (dict(confidence=0.9, user_safe=False, supported=False, t=0, can_ask=True), "refer", "unsafe_fault"),
    (dict(confidence=0.9, user_safe=True, supported=True, t=0, can_ask=True), "answer", "confident_and_supported"),
    (dict(confidence=0.9, user_safe=True, supported=False, t=1, can_ask=True), "ask", "continue"),
    (dict(confidence=0.9, user_safe=True, supported=False, t=6, can_ask=True), "refer", "unsupported"),
    (dict(confidence=0.5, user_safe=True, supported=True, t=2, can_ask=False), "refer", "no_useful_question"),
    (dict(confidence=0.5, user_safe=True, supported=True, t=6, can_ask=True), "refer", "turn_budget"),
])
def test_policy(args, action, reason):
    d = decide("f", tau=0.75, t_max=6, **{k: v for k, v in args.items()})
    assert (d.action, d.reason) == (action, reason)


def test_retrieval_query_uses_confirmed_facts_only(tfidf):
    q = build_query({"primary_symptom": "not_cooling", "condenser_coils_dusty": "yes"}, "dirty_condenser_coils",
                    {"dirty_condenser_coils": "Dirty condenser coils"})
    assert "coils" in q and "agalla" not in q
    hits = tfidf.search(q, 5)
    assert len(hits) == 5 and supports("dirty_condenser_coils", hits)


def test_understand_with_mock(mock_llm):
    u = understand("fridge cooling agalla compressor sound ide", mock_llm, k=8)
    assert u.n_valid == 8 and math.isclose(u.probs.sum(), 1.0)
    assert u.interpretations[0].get("primary_symptom") == "not_cooling"


def test_agent_end_to_end_with_mock(mock_llm, tfidf):
    from core.agent import Agent, AgentConfig
    agent = Agent(mock_llm, load_hypothesis_model(), tfidf, AgentConfig.from_yaml(T_max=4))
    turn = agent.start("My fridge is not cooling. I can hear the compressor running.")
    while turn.action == "ask":
        assert turn.question["kind"] in ("clarification", "diagnostic")
        turn = agent.reply("not sure")
    assert agent.result is not None and agent.result.turns <= 4
    assert agent.result.predicted == "REFER" or agent.result.predicted in agent.model.faults
    assert all({"H_L", "H_D", "H"} <= set(t.belief) for t in agent.turns)
