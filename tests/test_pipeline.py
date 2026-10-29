"""Smoke test of the experiment pipeline on the offline mock LLM:
run -> summary.json -> LaTeX tables / figures -> error analysis."""

import json
import sys

import pytest

import core.clarity
import core.llm
import eval.aggregate
import eval.error_analysis
import eval.run_experiment as rx
from core.retrieval import Retriever
from eval.export_latex import export


def _offline(tmp_path, monkeypatch, cfg):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-1")
    monkeypatch.setattr(core.llm, "CACHE_DIR", tmp_path / "llm")
    monkeypatch.setattr(core.clarity, "CLARITY_DIR", tmp_path / "clarity")
    monkeypatch.setattr(rx, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(rx, "RESULTS", tmp_path)
    monkeypatch.setattr(rx, "TUNING_FILE", tmp_path / "none.json")
    monkeypatch.setattr(rx, "make_retriever", lambda: Retriever(backend="tfidf"))
    monkeypatch.setattr(rx, "load_experiment", lambda profile: dict(cfg))


def test_interrupted_run_resumes_without_losing_records(tmp_path, monkeypatch):
    cfg = {"split": "test", "systems": ["b1_direct", "b3_infogain_dx"], "conditions": ["clean"], "seeds": [0],
           "max_cases": 3, "include_stress": False, "simulator": {"mode": "deterministic"}, "overrides": {},
           "hypothesis_weights": None, "clarity_model": None}
    _offline(tmp_path, monkeypatch, cfg)
    real_sim, started = rx.UserSimulator, []

    def flaky_sim(*a, **kw):  # Ctrl+C during the 4th record
        started.append(1)
        if len(started) == 4:
            raise KeyboardInterrupt
        return real_sim(*a, **kw)

    monkeypatch.setattr(rx, "UserSimulator", flaky_sim)
    monkeypatch.setattr(sys, "argv", ["run_experiment", "--yes"])
    with pytest.raises(KeyboardInterrupt):
        rx.main()
    run_dir = next((tmp_path / "runs").iterdir())
    assert json.loads((run_dir / "manifest.json").read_text())["status"] == "partial"
    with (run_dir / "b1_direct.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"variant_id": "cut off by a power')  # half-written record

    monkeypatch.setattr(rx, "UserSimulator", real_sim)
    monkeypatch.setattr(sys, "argv", ["run_experiment", "--resume", run_dir.name, "--yes"])
    with pytest.raises(SystemExit):
        rx.main()
    assert json.loads((run_dir / "manifest.json").read_text())["status"] == "complete"
    for name in cfg["systems"]:
        records = [json.loads(line) for line in (run_dir / f"{name}.jsonl").read_text().splitlines()]
        assert len(records) == len({r["variant_id"] for r in records}) == 3


@pytest.fixture()
def tiny_run(tmp_path, monkeypatch):
    cfg = {"split": "test", "systems": ["b1_direct", "b2_llm_questions", "b3_infogain_dx", "q2d", "q2d_minus_hl"],
           "conditions": ["clean", "codemixed_kn", "codemixed_hi"], "seeds": [0], "max_cases": 3,
           "include_stress": True, "simulator": {"mode": "deterministic"}, "overrides": {"K": 3},
           "hypothesis_weights": None, "clarity_model": None}
    _offline(tmp_path, monkeypatch, cfg)
    monkeypatch.setattr(sys, "argv", ["run_experiment", "--yes"])
    with pytest.raises(SystemExit):
        rx.main()
    run_dir = next((tmp_path / "runs").iterdir())
    return run_dir


def test_pipeline_end_to_end(tiny_run, tmp_path, monkeypatch):
    manifest = json.loads((tiny_run / "manifest.json").read_text())
    assert manifest["status"] == "complete" and manifest["llm"] == "mock/mock-1"
    summary = json.loads((tiny_run / "summary.json").read_text())
    assert set(summary["systems"]) == {"b1_direct", "b2_llm_questions", "b3_infogain_dx", "q2d", "q2d_minus_hl"}
    q = summary["main"]["q2d"]
    assert 0 <= q["all"]["macro_f1"][1] <= q["all"]["macro_f1"][0] <= q["all"]["macro_f1"][2] <= 1
    assert "codemixed" in summary["kn_vs_hi"]["q2d"] and summary["stress"]["q2d"]["n"] >= 1
    assert summary["trajectory"]["q2d"]["clean"]["H_D"]

    # Export refuses mock runs unless explicitly allowed.
    monkeypatch.setattr("eval.export_latex.RESULTS", tmp_path)
    with pytest.raises(SystemExit):
        export(tiny_run.name, tmp_path / "paper")
    written = export(tiny_run.name, tmp_path / "paper", allow_mock=True)
    assert "tables/main_results.tex" in written and "figures/hl_hd_trajectory.pdf" in written
    assert "Query2Diagnose" in (tmp_path / "paper" / "tables" / "main_results.tex").read_text()

    monkeypatch.setattr(eval.error_analysis, "RESULTS", tmp_path)
    report = eval.error_analysis.analyse(tiny_run.name)
    assert report.startswith("# Error analysis")


def test_only_main_runs_become_latest(tiny_run, tmp_path):
    # The tiny run is a main run, so it is what the tables and the website read.
    assert json.loads((tmp_path / "latest.json").read_text())["run_id"] == tiny_run.name
    base = {"simulator": {"mode": "deterministic"}, "hypothesis_weights": None}
    assert rx.is_main_run(base)
    assert not rx.is_main_run({**base, "hypothesis_weights": "flat"})
    assert not rx.is_main_run({**base, "simulator": {"mode": "noisy"}})


def test_side_tables_render(tiny_run):
    from eval.export_latex import table_noisy, table_sensitivity
    summary = json.loads((tiny_run / "summary.json").read_text())
    assert summary["hypothesis_weights"] is None
    runs = [{**summary, "hypothesis_weights": w} for w in ("sharp", "base")]
    tex = table_sensitivity(runs)
    assert tex.index("base &") < tex.index("sharp &") and "Query2Diagnose" in tex
    assert "Deterministic & Noisy" in table_noisy(summary, {**summary, "simulator": "noisy"})


def test_estimate_counts_greedy_calls_once_unless_the_simulator_is_noisy():
    from core.records import VARIANTS_FILE, Variant, read_jsonl
    variants = read_jsonl(VARIANTS_FILE, Variant)[:10]
    settings = core.llm.Settings.from_env(provider="mock", model="mock-1")
    cfg = {"systems": ["b3_infogain_dx", "b2_llm_questions", "q2d"], "seeds": [0, 1, 2], "overrides": {"K": 4},
           "simulator": {"mode": "deterministic"}}
    det = rx.estimate(cfg, variants, settings, need_clarity=False)["calls"]
    assert det["understand"] == 10 * 4 * 3 + 10 and det["b2_turn"] == 10 * 4
    noisy = rx.estimate({**cfg, "simulator": {"mode": "noisy"}}, variants, settings, need_clarity=False)["calls"]
    assert noisy["understand"] == det["understand"] and noisy["b2_turn"] == 3 * det["b2_turn"]


def test_local_model_is_free_and_reuses_the_saved_clarity_estimate(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "gpt-oss:20b")
    llm = core.llm.LLMClient(core.llm.Settings.from_env())
    assert llm.settings.price() == {"input": 0.0, "output": 0.0}
    clarity = rx.clarity_client(rx.load_experiment("pilot"), llm)
    assert clarity.name == "groq/openai/gpt-oss-120b"
    assert core.clarity.load_clarity(clarity.name), "A(q) estimate missing from data/clarity/"
