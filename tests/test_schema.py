import pytest
from pydantic import ValidationError

from core.schema import Attribute, load_schema


def test_schema_loads_with_expected_safety_flags():
    schema = load_schema()
    assert len(schema.faults) == 15
    assert schema.unsafe_faults == {
        "start_relay_capacitor", "compressor_failure", "sealed_system_refrigerant", "control_board_wiring",
    }


def test_attribute_values_are_strings():
    # Unquoted yes/no in YAML would load as booleans and silently break lookups.
    for name, attr in load_schema().attributes.items():
        assert all(isinstance(v, str) for v in attr.values), name


@pytest.mark.parametrize("effort, cost", [(1, 0.0), (2, 0.5), (3, 1.0)])
def test_cost_normalises_effort(effort, cost):
    assert Attribute(description="x", values=["a", "b"], effort=effort).cost == cost


@pytest.mark.parametrize("values", [["a", "a"], ["a", "not_sure"], ["unmentioned", "b"]])
def test_attribute_rejects_duplicate_or_reserved_values(values):
    with pytest.raises(ValidationError):
        Attribute(description="x", values=values, effort=1)
