"""Run systems x conditions x cases x seeds and save every transcript.

    python -I -m eval.run_experiment [--profile pilot] [--estimate-only] [--yes] [--resume RUN_ID]

Prints an estimated number of LLM calls, tokens and cost first and asks for
confirmation (rule: no paid calls above MAX_USD_PER_RUN without asking).
Writes results/runs/<run_id>/<system>.jsonl plus manifest.json (git hash,
config, model, date, cost) and, when every record exists, summary.json.
A run stopped by an exhausted quota is resumable: completed records are
skipped and cached LLM calls are free.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

import yaml

from core.agent import AgentConfig
from core.clarity import estimate_clarity, load_clarity
from core.hypothesis import load_hypothesis_model
from core.llm import BudgetExceeded, LLMClient, QuotaExhausted, Settings
from core.normalize import normalize
from core.paths import CONFIGS, RESULTS, ROOT
from core.records import CASES_FILE, STRESS_FILE, VARIANTS_FILE, Case, Variant, load_splits, read_jsonl
from core.retrieval import Retriever
from core.schema import load_schema
from sim.user_simulator import UserSimulator
from systems.base import SystemResult
from systems.registry import build_systems

RUNS = RESULTS / "runs"
TUNING_FILE = RESULTS / "tuning" / "best.json"

# Rough per-call token sizes (input, output incl. hidden reasoning) for the estimate.
TOKENS = {"understand": (900, 250), "direct": (1000, 300), "b2_turn": (1500, 300), "state_tracker": (1000, 250),
          "mock_user": (150, 120), "parse_answer": (200, 80)}


def load_experiment(profile: str | None) -> dict:
    cfg = yaml.safe_load((CONFIGS / "experiment.yaml").read_text(encoding="utf-8"))
    profiles = cfg.pop("profiles", {})
    if profile:
        cfg.update(profiles[profile])
        cfg["profile"] = profile
    return cfg


def select_variants(cfg: dict) -> tuple[list[Variant], dict[str, Case]]:
    cases = {c.case_id: c for c in read_jsonl(CASES_FILE, Case)}
    ids = load_splits()[cfg["split"]]
    if cfg.get("max_cases"):
        by_fault: dict[str, list[str]] = defaultdict(list)
        for cid in ids:
            by_fault[cases[cid].fault].append(cid)
        picked, k = [], 0
        while len(picked) < cfg["max_cases"] and any(by_fault.values()):
            for fault in load_schema().faults:
                if by_fault[fault] and len(picked) < cfg["max_cases"]:
                    picked.append(by_fault[fault].pop(0))
            k += 1
        ids = picked
    keep = set(ids)
    variants = [v for v in read_jsonl(VARIANTS_FILE, Variant) if v.case_id in keep and v.condition in cfg["conditions"]]
    if cfg.get("include_stress"):
        variants += [v for v in read_jsonl(STRESS_FILE, Variant) if v.case_id in keep]
    return variants, cases


def estimate(cfg: dict, variants: list[Variant], settings: Settings, need_clarity: bool) -> dict:
    agent = AgentConfig.from_yaml(**cfg.get("overrides", {}))
    seeds = len(cfg["seeds"])
    calls: dict[str, int] = defaultdict(int)
    changed = sum(bool(normalize(v.text).changes) for v in variants)
    for name in cfg["systems"]:
        if name in ("q2d", "q2d_minus_cost_clarity"):
            if name == "q2d" or "q2d" not in cfg["systems"]:
                calls["understand"] += len(variants) * agent.K * seeds
        elif name in ("b3_infogain_dx", "q2d_minus_hl"):
            if name == "b3_infogain_dx" or "b3_infogain_dx" not in cfg["systems"]:
                calls["understand"] += len(variants)
        elif name == "q2d_minus_normalisation":
            calls["understand"] += changed * agent.K * seeds
        elif name == "q2d_minus_fault_state":
            calls["state_tracker"] += len(variants) * (agent.T_max + 1)
        elif name == "b1_direct":
            calls["direct"] += len(variants)
        elif name == "b2_llm_questions":
            calls["b2_turn"] += len(variants) * 4
    if need_clarity:
        n_values = sum(len(a.values) for n, a in load_schema().attributes.items() if n != "device")
        calls["mock_user"] += n_values * 3
        calls["parse_answer"] += n_values
    price = settings.price()
    tin = sum(n * TOKENS[t][0] for t, n in calls.items())
    tout = sum(n * TOKENS[t][1] for t, n in calls.items())
    return {"calls": dict(calls), "total_calls": sum(calls.values()), "input_tokens": tin, "output_tokens": tout,
            "usd_if_paid": round((tin * price["input"] + tout * price["output"]) / 1e6, 2)}


def make_retriever() -> Retriever:
    r = yaml.safe_load((CONFIGS / "agent.yaml").read_text(encoding="utf-8"))["retrieval"]
    return Retriever(backend=r["backend"], model_name=r["model"], chunk_words=r["chunk_words"],
                     overlap=r["overlap_words"])


def git_state() -> dict:
    def run(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def tuned_params() -> dict:
    return json.loads(TUNING_FILE.read_text(encoding="utf-8")) if TUNING_FILE.exists() else {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the experiment grid.")
    ap.add_argument("--profile")
    ap.add_argument("--resume", metavar="RUN_ID")
    ap.add_argument("--estimate-only", action="store_true")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--weights", help="hypothesis weight set from configs/hypothesis.yaml (sensitivity)")
    args = ap.parse_args()

    run_dir = RUNS / args.resume if args.resume else None
    cfg = (json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["config"] if run_dir
           else load_experiment(args.profile))
    if args.weights and not run_dir:
        cfg["hypothesis_weights"] = args.weights
        args.profile = f"{args.profile or 'run'}-{args.weights}"
    settings = Settings.from_env()
    llm = LLMClient(settings)
    variants, cases = select_variants(cfg)
    clarity_llm_name = cfg.get("clarity_model") or settings.model
    clarity_client = llm if clarity_llm_name == settings.model else LLMClient(Settings.from_env(model=clarity_llm_name))
    clarity = load_clarity(clarity_client.name)
    est = estimate(cfg, variants, settings, need_clarity=clarity is None)
    print(f"LLM: {llm.name} | variants: {len(variants)} | seeds: {cfg['seeds']} | systems: {cfg['systems']}")
    print(f"estimated calls (before cache hits): {est['calls']} -> {est['total_calls']} requests, "
          f"~{est['input_tokens'] / 1e6:.2f}M in / {est['output_tokens'] / 1e6:.2f}M out tokens, "
          f"~${est['usd_if_paid']} at paid-tier prices (MAX_USD_PER_RUN={settings.max_usd})")
    if settings.provider == "groq":
        daily = yaml.safe_load((CONFIGS / "llm.yaml").read_text(encoding="utf-8"))["free_tier_daily"]
        days = max(est["total_calls"] / daily["requests"], (est["input_tokens"] + est["output_tokens"]) / daily["tokens"])
        print(f"on the Groq free tier ({daily['tokens']:,} tokens and {daily['requests']:,} requests per day per model) "
              f"this is ~{days:.1f} day(s); a paid tier removes the daily caps")
    if args.estimate_only:
        return
    if est["usd_if_paid"] > settings.max_usd:
        print("note: the paid-tier estimate exceeds MAX_USD_PER_RUN; the client stops paid calls at that limit")
    if not args.yes and input("Run now? [y/N] ").strip().lower() != "y":
        print("aborted")
        return

    if clarity is None and any(s.startswith("q2d") for s in cfg["systems"]):
        print(f"estimating A(q) with {clarity_client.name} ...")
        clarity = estimate_clarity(clarity_client)["A"]
    tuned = tuned_params()
    model = load_hypothesis_model(cfg.get("hypothesis_weights"))
    retriever = make_retriever()
    base_overrides = {**cfg.get("overrides", {}), **{k: tuned[k] for k in ("lambda_", "mu") if k in tuned}}
    systems = build_systems(cfg["systems"], llm, model, retriever, clarity, base_overrides)

    if run_dir is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + (f"-{args.profile}" if args.profile else "")
        run_dir = RUNS / run_id
        run_dir.mkdir(parents=True)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "run_id": run_dir.name, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": cfg, "llm": llm.name, "clarity_llm": clarity_client.name, "git": git_state(),
        "tuned": tuned, "agent_config": vars(AgentConfig.from_yaml(**base_overrides)),
        "n_variants": len(variants), "n_cases": len({v.case_id for v in variants}), "estimate": est,
        "ledger": [], "status": "running"}

    done: dict[str, set] = {}
    for name in cfg["systems"]:
        path = run_dir / f"{name}.jsonl"
        done[name] = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                done[name].add((r["variant_id"], r["seed"]))
    total = len(variants) * len(cfg["seeds"]) * len(cfg["systems"])
    status = "complete"
    try:
        n = sum(len(d) for d in done.values())
        for v in variants:
            for seed in cfg["seeds"]:
                lang = v.lang_pair.split("-")[0] if v.lang_pair in ("kn-en", "hi-en") else "en"
                for name, system in systems.items():
                    if (v.variant_id, seed) in done[name]:
                        continue
                    sim = UserSimulator(cases[v.case_id], mode=cfg["simulator"]["mode"], lang=lang, seed=seed)
                    result: SystemResult = system.run(v, sim, seed)
                    with (run_dir / f"{name}.jsonl").open("a", encoding="utf-8") as f:
                        f.write(result.model_dump_json() + "\n")
                    n += 1
                    if n % 25 == 0:
                        print(f"  {n}/{total} records | {llm.ledger.summary()}", flush=True)
    except (QuotaExhausted, BudgetExceeded) as e:
        status = "partial"
        print(f"stopped: {e}\nresume with: python -I -m eval.run_experiment --resume {run_dir.name}")
    manifest["ledger"].append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **llm.ledger.summary()})
    manifest["status"] = status
    manifest["cost_usd"] = round(sum(e["cost_usd"] for e in manifest["ledger"]), 4)
    manifest_path.write_text(json.dumps(manifest, indent=1, default=str) + "\n", encoding="utf-8")
    if status == "complete":
        from eval.aggregate import summarize
        summarize(run_dir)
        (RESULTS / "latest.json").write_text(json.dumps({"run_id": run_dir.name}) + "\n", encoding="utf-8")
        print(f"complete -> {run_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
