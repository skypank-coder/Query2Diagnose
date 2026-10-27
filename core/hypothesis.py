"""Hypothesis model p(attribute = value | fault), paper Sec. III-D.

Compiled from data/hypothesis_model.yaml. Each (fault, attribute) row comes
from, in order of precedence:

1. an explicit row that tags values typical / possible / atypical and cites
   the passages (or the schema definition) behind every tag;
2. otherwise the single-fault healthy default: an attribute the fault does not
   involve shows its working-unit value (`healthy` section);
3. otherwise uniform.

For primary_symptom, a symptom whose iFixit page enumerates its causes is
`closed_world`: a fault whose row does not tag that symptom gets the
`unlisted` level instead of `untagged`. Level weights come from
configs/hypothesis.yaml so the sensitivity experiment can swap them.

The compiled table supplies p(z | s) in eq. (1) and the answer likelihoods in
eq. (2).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, Field, model_validator

from core.paths import HYPOTHESIS_CONFIG, HYPOTHESIS_FILE
from core.schema import FaultSchema, load_schema

Level = Literal["typical", "possible", "atypical", "unlisted"]
Source = Literal["cited", "definitional", "healthy", "uniform"]


class Row(BaseModel):
    tags: dict[str, Level]
    cites: list[str] = []
    definitional: list[str] = []  # tagged values justified by the schema definition
    rationale: str | None = None

    @model_validator(mode="after")
    def _provenance(self) -> Row:
        if stray := set(self.definitional) - set(self.tags):
            raise ValueError(f"definitional values not tagged: {stray}")
        if self.definitional and not self.rationale:
            raise ValueError("definitional tags need a rationale")
        if set(self.tags) - set(self.definitional) and not self.cites:
            raise ValueError("tags not marked definitional need at least one cited passage")
        return self


class Healthy(BaseModel):
    rationale: str
    values: dict[str, list[str]]             # attribute -> working-unit values


class HypothesisSpec(BaseModel):
    version: str
    healthy: Healthy | None = None
    closed_world: dict[str, dict[str, list[str]]] = {}  # attribute -> value -> page passages
    defaults: dict[str, Row] = {}            # attribute -> row applied to every fault
    rows: dict[str, dict[str, Row]]          # fault -> attribute -> row

    def row(self, fault: str, attribute: str) -> Row | None:
        return self.rows.get(fault, {}).get(attribute) or self.defaults.get(attribute)

    def source(self, fault: str, attribute: str) -> Source:
        row = self.row(fault, attribute)
        if row is not None:
            return "cited" if row.cites else "definitional"
        if self.healthy and attribute in self.healthy.values:
            return "healthy"
        return "uniform"


class LevelWeights(BaseModel):
    typical: float = Field(gt=0)
    possible: float = Field(gt=0)
    atypical: float = Field(gt=0)
    unlisted: float = Field(gt=0)


class HypothesisConfig(BaseModel):
    levels: LevelWeights
    untagged: Level = "possible"
    epsilon: float = Field(ge=0, lt=1)
    sensitivity: dict[str, LevelWeights] = {}


@dataclass(frozen=True)
class HypothesisModel:
    schema: FaultSchema
    spec: HypothesisSpec
    faults: tuple[str, ...]
    # attribute -> array of shape (n_faults, n_values); each row sums to 1
    table: dict[str, np.ndarray]

    def likelihood(self, attribute: str, value: str) -> np.ndarray:
        """p(attribute = value | z) for every fault z, in `faults` order."""
        values = self.schema.attributes[attribute].values
        return self.table[attribute][:, values.index(value)]

    def distribution(self, fault: str, attribute: str) -> dict[str, float]:
        values = self.schema.attributes[attribute].values
        probs = self.table[attribute][self.faults.index(fault)]
        return dict(zip(values, probs.tolist()))

    def fault_posterior(self, observed: dict[str, str]) -> np.ndarray:
        """p(z | observed attribute values) under a uniform prior (naive Bayes),
        i.e. p(z | s) for one interpretation s; computed in log space."""
        log_p = np.zeros(len(self.faults))
        for attribute, value in observed.items():
            log_p += np.log(self.likelihood(attribute, value))
        log_p -= log_p.max()
        p = np.exp(log_p)
        return p / p.sum()


def validate_spec(spec: HypothesisSpec, schema: FaultSchema) -> None:
    def check_values(where: str, attribute: str, values) -> None:
        if attribute not in schema.attributes:
            raise ValueError(f"{where}: unknown attribute {attribute}")
        if bad := set(values) - set(schema.attributes[attribute].values):
            raise ValueError(f"{where}: unknown values {bad}")

    for attribute, row in spec.defaults.items():
        check_values(f"defaults.{attribute}", attribute, row.tags)
    for fault, attrs in spec.rows.items():
        if fault not in schema.faults:
            raise ValueError(f"rows.{fault}: unknown fault")
        for attribute, row in attrs.items():
            check_values(f"rows.{fault}.{attribute}", attribute, row.tags)
    if spec.healthy:
        for attribute, values in spec.healthy.values.items():
            check_values(f"healthy.{attribute}", attribute, values)
    for attribute, values in spec.closed_world.items():
        check_values(f"closed_world.{attribute}", attribute, values)


def cited_passages(spec: HypothesisSpec) -> set[str]:
    rows = list(spec.defaults.values()) + [r for a in spec.rows.values() for r in a.values()]
    ids = {pid for r in rows for pid in r.cites}
    ids |= {pid for vals in spec.closed_world.values() for pids in vals.values() for pid in pids}
    return ids


def row_levels(spec: HypothesisSpec, config: HypothesisConfig, fault: str, attribute: str,
               values: list[str]) -> list[Level] | None:
    """Level of every value in the (fault, attribute) row, or None if uniform."""
    row = spec.row(fault, attribute)
    if row is not None:
        tags = dict(row.tags)
    elif spec.healthy and attribute in spec.healthy.values:
        tags = {v: "typical" for v in spec.healthy.values[attribute]}
    else:
        tags = None
    closed = spec.closed_world.get(attribute, {})
    if tags is None and not closed:
        return None
    tags = tags or {}
    return [tags.get(v, "unlisted" if v in closed else config.untagged) for v in values]


def compile_model(schema: FaultSchema, spec: HypothesisSpec, config: HypothesisConfig,
                  weights: LevelWeights | None = None) -> HypothesisModel:
    validate_spec(spec, schema)
    w = (weights or config.levels).model_dump()
    faults = tuple(schema.faults)
    table = {}
    for attribute, attr in schema.attributes.items():
        n = len(attr.values)
        probs = np.empty((len(faults), n))
        for i, fault in enumerate(faults):
            levels = row_levels(spec, config, fault, attribute, attr.values)
            if levels is None:
                p = np.full(n, 1.0 / n)
            else:
                raw = np.array([w[level] for level in levels])
                p = raw / raw.sum()
            probs[i] = (p + config.epsilon) / (1 + config.epsilon * n)
        table[attribute] = probs
    return HypothesisModel(schema=schema, spec=spec, faults=faults, table=table)


def load_spec() -> HypothesisSpec:
    return HypothesisSpec.model_validate(yaml.safe_load(HYPOTHESIS_FILE.read_text(encoding="utf-8")))


def load_config() -> HypothesisConfig:
    return HypothesisConfig.model_validate(yaml.safe_load(HYPOTHESIS_CONFIG.read_text(encoding="utf-8")))


@lru_cache(maxsize=8)
def load_hypothesis_model(weight_set: str | None = None) -> HypothesisModel:
    """Load the model; `weight_set` names an entry of `sensitivity` in the config."""
    config = load_config()
    weights = config.sensitivity[weight_set] if weight_set else None
    return compile_model(load_schema(), load_spec(), config, weights)
