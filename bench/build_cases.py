"""Build underlying benchmark cases from the scenarios in
data/benchmark/scenarios.yaml (each tied to one source passage).

A case fixes the hidden fault z*, the full ground-truth attribute vector
(scenario values + healthy defaults, never sampled from the hypothesis model),
a clean English description that mentions a subset of attributes, and the gold
action (decision 10). The gold action does not depend on the hypothesis model:

- REFER if z* is unsafe;
- REFER if the full observable state is *underdetermined*, i.e. some scenario
  of another fault can produce exactly the same attribute vector, so no
  question in the schema can tell the faults apart;
- z* otherwise.

`oracle_posterior` = p(z* | all attributes) under the hypothesis model is kept
as a diagnostic (the model's ceiling), not used for labels.
Output: data/benchmark/cases.jsonl (provenance: synthetic).
"""

from __future__ import annotations

import itertools
import random
from collections import Counter
from functools import lru_cache

import yaml

from bench.render import IMPLICIT, render, symptom_has_where
from core.hypothesis import load_hypothesis_model
from core.paths import CONFIGS, DATA
from core.records import CASES_FILE, REFER, Case, write_jsonl
from core.schema import load_schema

GENERATOR = "scenario-templates-v1"
SCENARIOS_FILE = DATA / "benchmark" / "scenarios.yaml"


def load_config() -> dict:
    return yaml.safe_load((CONFIGS / "benchmark.yaml").read_text(encoding="utf-8"))


def load_scenarios() -> dict[str, list[dict]]:
    return yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8"))


def materialize(choice: dict[str, str], fixed: set[str]) -> dict[str, str]:
    """Apply physical consistency to one choice of values; `fixed` are the
    attributes the scenario sets (left untouched where a rule allows)."""
    attrs = dict(choice)
    if attrs["cooling_type"] == "direct_cool":
        attrs["condenser_fan_running"] = attrs["evaporator_fan_running"] = "not_applicable"
        if "error_code" not in fixed:
            attrs["error_code"] = "no_display"
    if attrs["power_supply_ok"] == "no":
        attrs["compressor_running"], attrs["noise_type"] = "no", "none"
        for fan in ("condenser_fan_running", "evaporator_fan_running"):
            if attrs[fan] != "not_applicable":
                attrs[fan] = "no"
    if attrs["compressor_running"] == "no" and "noise_type" not in fixed:
        attrs["noise_type"] = "none"
    if attrs["noise_type"] in ("none", "normal_hum"):
        attrs["noise_location"] = "not_applicable"
    return attrs


def _options(scenario: dict, healthy: dict) -> dict[str, list[str]]:
    merged = {**healthy, **scenario["attributes"]}
    return {a: (v if isinstance(v, list) else [v]) for a, v in merged.items()}


def sample_attributes(scenario: dict, healthy: dict, rng: random.Random) -> dict[str, str]:
    choice = {a: rng.choice(vals) for a, vals in _options(scenario, healthy).items()}
    return materialize(choice, set(scenario["attributes"]))


def possible_states(scenario: dict, healthy: dict) -> set[tuple]:
    """Every attribute vector the scenario can produce."""
    options = _options(scenario, healthy)
    names = sorted(options)
    states = set()
    for values in itertools.product(*(options[a] for a in names)):
        attrs = materialize(dict(zip(names, values)), set(scenario["attributes"]))
        states.add(tuple(sorted(attrs.items())))
    return states


@lru_cache(maxsize=1)
def _state_index() -> dict[tuple, frozenset[str]]:
    """attribute vector -> faults whose scenarios can produce it."""
    cfg, index = load_config(), {}
    for fault, scenarios in load_scenarios().items():
        for scenario in scenarios:
            for state in possible_states(scenario, cfg["healthy"]):
                index.setdefault(state, set()).add(fault)
    return {s: frozenset(f) for s, f in index.items()}


def confusable_faults(fault: str, attrs: dict[str, str]) -> list[str]:
    return sorted(_state_index()[tuple(sorted(attrs.items()))] - {fault})


def choose_mentions(attrs: dict[str, str], scenario: dict, cfg: dict, rng: random.Random) -> list[str]:
    mentions = ["device", "primary_symptom"]
    if symptom_has_where("en", attrs["primary_symptom"]) and rng.random() < cfg["p_mention_compartment"]:
        mentions.append("compartment_affected")
    specific = set(scenario["attributes"]) - {"primary_symptom", "compartment_affected"}
    skip = IMPLICIT | {"primary_symptom", "compartment_affected"}
    pool = [a for a in attrs if a not in skip
            and (a in specific or a not in cfg["mention_only_if_specific"])]
    weights = [cfg["scenario_attribute_weight"] if a in specific else 1.0 for a in pool]
    k = rng.choices(list(cfg["extra_mentions"]), weights=list(cfg["extra_mentions"].values()))[0]
    for _ in range(k):
        a = rng.choices(pool, weights=weights)[0]
        i = pool.index(a)
        pool.pop(i), weights.pop(i)
        mentions.append(a)
    return mentions


def build() -> list[Case]:
    cfg, schema, model = load_config(), load_schema(), load_hypothesis_model()
    scenarios = load_scenarios()
    rng = random.Random(cfg["seed"])
    cases: list[Case] = []
    seen: set[tuple] = set()
    for fault in schema.faults:
        fault_scenarios = scenarios[fault]
        for i in range(cfg["cases_per_fault"]):
            scenario = fault_scenarios[i % len(fault_scenarios)]
            for _attempt in range(20):          # avoid duplicate (attributes, description) cases
                attrs = sample_attributes(scenario, cfg["healthy"], rng)
                mentions = choose_mentions(attrs, scenario, cfg, rng)
                description, known = render(mentions, attrs, lambda _a: "en", rng)
                key = (tuple(sorted(attrs.items())), description)
                if key not in seen:
                    break
            seen.add(key)
            known = [a for a in schema.attributes if a in known]

            confusable = confusable_faults(fault, attrs)
            if not schema.faults[fault].user_safe:
                action, reason = REFER, "unsafe_fault"
            elif confusable:
                action, reason = REFER, "underdetermined"
            else:
                action, reason = fault, "identifiable"
            full = model.fault_posterior(attrs)
            partial = model.fault_posterior({a: attrs[a] for a in known})
            order = partial.argsort()[::-1]
            candidates = [model.faults[j] for j in order if partial[j] >= cfg["candidate_min_prob"]]

            cases.append(Case(
                case_id=f"c{len(cases) + 1:04d}",
                scenario_id=scenario["id"],
                fault=fault,
                safety_flag="diy_ok" if schema.faults[fault].user_safe else "refer",
                gold_action=action,
                gold_action_reason=reason,
                confusable_faults=confusable,
                oracle_posterior=round(float(full[model.faults.index(fault)]), 4),
                attributes=attrs,
                known_attributes=known,
                unknown_attributes=[a for a in schema.attributes if a not in known],
                candidate_faults=candidates,
                description=description,
                source_passage_id=scenario["passage"],
                provenance="synthetic",
                generator=GENERATOR,
            ))
    return cases


def main() -> None:
    cfg = load_config()
    cases = build()
    write_jsonl(CASES_FILE, cases)
    print(f"{len(cases)} cases -> {CASES_FILE.relative_to(DATA.parent)}")
    print("gold action:", dict(Counter(c.gold_action_reason for c in cases)))
    under = Counter(c.fault for c in cases if c.gold_action_reason == "underdetermined")
    if under:
        print("underdetermined by fault:", dict(under))
    ident = [c for c in cases if c.gold_action_reason == "identifiable"]
    ceiling = sum(c.oracle_posterior >= cfg["oracle_tau"] for c in ident)
    print(f"model ceiling: {ceiling}/{len(ident)} identifiable cases reach tau={cfg['oracle_tau']} "
          "with every attribute known")


if __name__ == "__main__":
    main()
