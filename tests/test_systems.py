import pytest

from core.hypothesis import load_hypothesis_model
from core.llm import LLMClient, Settings
from core.questions import render_question, templates
from core.records import CASES_FILE, REFER, VARIANTS_FILE, Case, Variant, read_jsonl
from core.retrieval import Retriever
from core.schema import NOT_SURE, load_schema
from sim.user_simulator import UserSimulator, question_to_attribute
from systems.base import SystemResult
from systems.registry import ALL, build_systems


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    import core.llm as llm_mod
    llm_mod.CACHE_DIR = tmp_path_factory.mktemp("llm-cache")
    llm = LLMClient(Settings.from_env(provider="mock", model="mock-1"))
    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    variants = read_jsonl(VARIANTS_FILE, Variant)
    return llm, Retriever(backend="tfidf"), cases, variants


def test_simulator_understands_every_q2d_question():
    for attribute in templates()["attributes"]:
        q = render_question(attribute, "diagnostic")
        assert question_to_attribute(q.text) == attribute, (attribute, q.text)


def test_deterministic_simulator_is_truthful_and_never_reveals_the_fault(setup):
    _, _, cases, _ = setup
    schema = load_schema()
    for case in list(cases.values())[::25]:
        sim = UserSimulator(case)
        for attribute in schema.attributes:
            if attribute == "device":
                continue
            ans = sim.answer(render_question(attribute, "diagnostic").text)
            assert ans.value == case.attributes[attribute]
            text = ans.text.lower()
            assert case.fault not in text and schema.faults[case.fault].name.lower() not in text
        assert sim.answer("What is your favourite colour?").value is None


def test_noisy_simulator_errors_and_not_sure(setup):
    _, _, cases, _ = setup
    case = next(iter(cases.values()))
    wrong = UserSimulator(case, mode="noisy", error_rate=1.0, not_sure_rate=0.0, typo_rate=0.0)
    assert wrong.answer("", "compressor_running").value != case.attributes["compressor_running"]
    unsure = UserSimulator(case, mode="noisy", error_rate=0.0, not_sure_rate=1.0, lang="hi")
    assert unsure.answer("", "compressor_running").value == NOT_SURE
    kn = UserSimulator(case, mode="noisy", error_rate=0.0, not_sure_rate=0.0, typo_rate=0.0, lang="kn")
    value = case.attributes["compressor_running"]
    assert kn.answer("", "compressor_running").text == templates()["attributes"]["compressor_running"]["options"][value]["kn"]


def test_every_system_runs_and_returns_the_shared_schema(setup):
    llm, retriever, cases, variants = setup
    model = load_hypothesis_model()
    systems = build_systems(ALL, llm, model, retriever, clarity={})
    sample = [v for v in variants if v.condition in ("clean", "codemixed_kn", "combined_hi")][:3]
    for name, system in systems.items():
        for v in sample:
            r = system.run(v, UserSimulator(cases[v.case_id]), seed=0)
            assert isinstance(r, SystemResult) and r.system == name
            assert r.predicted == REFER or r.predicted in model.faults
            assert 0 <= r.turns <= 6 and 0.0 <= r.confidence <= 1.0


def test_b3_tracks_only_diagnostic_uncertainty(setup):
    llm, retriever, cases, variants = setup
    b3 = build_systems(["b3_infogain_dx"], llm, load_hypothesis_model(), retriever, clarity={})["b3_infogain_dx"]
    v = next(v for v in variants if v.condition == "codemixed_kn")
    r = b3.run(v, UserSimulator(cases[v.case_id]), seed=0)
    assert all(t["belief"]["H_L"] == 0.0 for t in r.transcript)
    assert all(t["question"] is None or t["question"]["kind"] == "diagnostic" for t in r.transcript)
