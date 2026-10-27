"""Hypothesis model p(attribute = value | fault), paper Sec. III-D.

Compiled from data/hypothesis_model.yaml, where each (fault, attribute) row
tags some values typical / possible / atypical and records the source passages
(or the schema definition) behind every tag. Untagged values take the
`untagged` level and attributes without a row are uniform. Level weights come
from configs/hypothesis.yaml so the sensitivity experiment can swap them.

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

Level = Literal["typical", "possible", "atypical"]


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


class HypothesisSpec(BaseModel):
    version: str
    defaults: dict[str, Row] = {}            # attribute -> row applied to every fault
    rows: dict[str, dict[str, Row]]          # fault -> attribute -> row

    def row(self, fault: str, attribute: str) -> Row | None:
        return self.rows.get(fault, {}).get(attribute) or self.defaults.get(attribute)


class LevelWeights(BaseModel):
    typical: float = Field(gt=0)
    possible: float = Field(gt=0)
    atypical: float = Field(gt=0)


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


def validate_spec(spec: HypothesisSpec, schema: FaultSchema) -> None:
    rows = [("(defaults)", a, r) for a, r in spec.defaults.items()]
    rows += [(z, a, r) for z, attrs in spec.rows.items() for a, r in attrs.items()]
    for fault, attribute, row in rows:
        where = f"{fault}.{attribute}"
        if fault != "(defaults)" and fault not in schema.faults:
            raise ValueError(f"{where}: unknown fault")
        if attribute not in schema.attributes:
            raise ValueError(f"{where}: unknown attribute")
        if bad := set(row.tags) - set(schema.attributes[attribute].values):
            raise ValueError(f"{where}: unknown values {bad}")


def cited_passages(spec: HypothesisSpec) -> set[str]:
    rows = list(spec.defaults.values()) + [r for a in spec.rows.values() for r in a.values()]
    return {pid for r in rows for pid in r.cites}


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
            row = spec.row(fault, attribute)
            if row is None:
                p = np.full(n, 1.0 / n)
            else:
                raw = np.array([w[row.tags.get(v, config.untagged)] for v in attr.values])
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
