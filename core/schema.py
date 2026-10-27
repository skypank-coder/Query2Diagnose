"""Fault schema (data/schema/fault_schema.yaml): attributes, allowed values,
user effort, and fault categories with their safety flag."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from core.paths import SCHEMA_FILE

UNMENTIONED = "unmentioned"  # interpretation value: attribute not in the message
NOT_SURE = "not_sure"        # answer value: user cannot tell
RESERVED_VALUES = {UNMENTIONED, NOT_SURE}


class Attribute(BaseModel):
    description: str
    values: list[str] = Field(min_length=2)
    effort: int = Field(ge=1, le=3)

    @field_validator("values")
    @classmethod
    def _distinct_unreserved(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values):
            raise ValueError(f"duplicate values in {values}")
        if clash := RESERVED_VALUES & set(values):
            raise ValueError(f"reserved values used as attribute values: {clash}")
        return values

    @property
    def cost(self) -> float:
        """C(q) in eq. (3): effort normalised to [0, 1]."""
        return (self.effort - 1) / 2


class Fault(BaseModel):
    name: str
    user_safe: bool


class FaultSchema(BaseModel):
    version: str
    device_scope: str
    attributes: dict[str, Attribute]
    faults: dict[str, Fault]

    @property
    def unsafe_faults(self) -> set[str]:
        return {z for z, f in self.faults.items() if not f.user_safe}


@lru_cache(maxsize=4)
def load_schema(path: Path = SCHEMA_FILE) -> FaultSchema:
    return FaultSchema.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
