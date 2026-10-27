import numpy as np
import pytest
from pydantic import ValidationError

from core.hypothesis import (
    HypothesisConfig, HypothesisSpec, Row, cited_passages, compile_model, load_config,
    load_hypothesis_model, load_spec,
)
from core.schema import FaultSchema
from core.sources import load_passages

TOY_SCHEMA = FaultSchema.model_validate({
    "version": "t", "device_scope": "toy",
    "attributes": {
        "colour": {"description": "c", "values": ["red", "green", "blue"], "effort": 1},
        "size": {"description": "s", "values": ["small", "large"], "effort": 2},
    },
    "faults": {"f1": {"name": "F1", "user_safe": True}, "f2": {"name": "F2", "user_safe": False}},
})
TOY_CONFIG = HypothesisConfig.model_validate({
    "levels": {"typical": 1.0, "possible": 0.25, "atypical": 0.01, "unlisted": 0.05},
    "untagged": "possible", "epsilon": 0.001,
})


def toy_model(rows, defaults=None, healthy=None, closed_world=None):
    spec = HypothesisSpec.model_validate({"version": "t", "rows": rows, "defaults": defaults or {},
                                          "healthy": healthy, "closed_world": closed_world or {}})
    return compile_model(TOY_SCHEMA, spec, TOY_CONFIG)


def test_compile_matches_hand_computation():
    model = toy_model({"f1": {"colour": {"tags": {"red": "typical", "green": "atypical"}, "cites": ["p1"]}}})
    # weights red=1, green=0.01, blue (untagged -> possible)=0.25; sum 1.26
    # p = (1/1.26, 0.01/1.26, 0.25/1.26) = (0.793651, 0.007937, 0.198413)
    # smoothed (p + 0.001) / (1 + 3 * 0.001) = (0.792274, 0.008910, 0.198817)
    assert model.distribution("f1", "colour") == pytest.approx(
        {"red": 0.792274, "green": 0.008910, "blue": 0.198817}, abs=1e-6)


def test_attribute_without_row_is_uniform():
    model = toy_model({"f1": {"colour": {"tags": {"red": "typical"}, "cites": ["p1"]}}})
    assert model.distribution("f2", "colour") == pytest.approx({v: 1 / 3 for v in ("red", "green", "blue")})
    assert model.distribution("f1", "size") == pytest.approx({"small": 0.5, "large": 0.5})


def test_fault_row_overrides_default():
    default = {"size": {"tags": {"small": "typical"}, "definitional": ["small"], "rationale": "r"}}
    model = toy_model({"f2": {"size": {"tags": {"large": "typical"}, "cites": ["p1"]}}}, default)
    assert model.distribution("f1", "size")["small"] > 0.7
    assert model.distribution("f2", "size")["large"] > 0.7


def test_healthy_default_applies_only_without_a_row():
    healthy = {"rationale": "single fault", "values": {"size": ["small"]}}
    model = toy_model({"f1": {"size": {"tags": {"large": "typical"}, "cites": ["p1"]}}}, healthy=healthy)
    # f2 has no row: small typical (1), large possible (0.25) -> 0.8 / 0.2 before smoothing
    # smoothed: (0.8 + 0.001) / 1.002 = 0.799401
    assert model.distribution("f2", "size")["small"] == pytest.approx(0.799401, abs=1e-6)
    assert model.distribution("f1", "size")["large"] > 0.7
    assert model.spec.source("f2", "size") == "healthy" and model.spec.source("f2", "colour") == "uniform"


def test_closed_world_marks_untagged_symptoms_unlisted():
    model = toy_model({"f1": {"colour": {"tags": {"red": "typical"}, "cites": ["p1"]}}},
                      closed_world={"colour": {"green": ["page"]}})
    # f1: red 1, green unlisted 0.05, blue possible 0.25 -> 1/1.3, 0.05/1.3, 0.25/1.3
    d = model.distribution("f1", "colour")
    assert d["green"] == pytest.approx((0.05 / 1.3 + 0.001) / 1.003, abs=1e-6)
    # f2 has no row: green unlisted, others possible
    assert model.distribution("f2", "colour")["green"] == pytest.approx((0.05 / 0.55 + 0.001) / 1.003, abs=1e-6)


def test_likelihood_is_a_vector_over_faults():
    model = toy_model({"f1": {"size": {"tags": {"small": "typical"}, "cites": ["p1"]}}})
    np.testing.assert_allclose(model.likelihood("size", "small"),
                               [model.distribution("f1", "size")["small"], 0.5])


@pytest.mark.parametrize("row", [
    {"tags": {"red": "typical"}},                                        # no cite, not definitional
    {"tags": {"red": "typical"}, "definitional": ["red"]},               # definitional without rationale
    {"tags": {"red": "typical"}, "cites": ["p"], "definitional": ["blue"], "rationale": "r"},  # untagged
])
def test_row_requires_provenance(row):
    with pytest.raises(ValidationError):
        Row.model_validate(row)


def test_unknown_value_is_rejected():
    with pytest.raises(ValueError, match="unknown values"):
        toy_model({"f1": {"colour": {"tags": {"purple": "typical"}, "cites": ["p1"]}}})


def test_real_model_rows_are_distributions():
    model = load_hypothesis_model()
    for attribute, table in model.table.items():
        assert table.shape[0] == len(model.faults)
        np.testing.assert_allclose(table.sum(axis=1), 1.0, err_msg=attribute)
        assert (table > 0).all(), attribute


def test_every_citation_resolves_to_a_passage():
    assert cited_passages(load_spec()) - set(load_passages()) == set()


def test_every_fault_has_a_cited_symptom_row():
    spec = load_spec()
    for fault in load_hypothesis_model().faults:
        row = spec.rows.get(fault, {}).get("primary_symptom")
        assert row is not None and row.cites, fault


def test_sensitivity_weight_sets_compile_and_base_matches_levels():
    config = load_config()
    assert config.sensitivity["base"] == config.levels
    for name in config.sensitivity:
        load_hypothesis_model(name)
