"""Pydantic schemas for template suite JSON (schema_version 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SCHEMA_VERSION = "1"


class ScenarioInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["scenario"] = "scenario"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    golden: dict[str, Any]


class DecisionQueryInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["decision_query"] = "decision_query"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    query: dict[str, Any]
    golden: dict[str, Any]


class RuleAttributionInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["rule_attribution"] = "rule_attribution"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    query: dict[str, Any]
    golden: dict[str, Any]


class BoundaryInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["boundary"] = "boundary"
    instance_id: str
    world_base: dict[str, int | bool] = Field(default_factory=dict)
    axis_variable: str
    values: list[int | bool] = Field(min_length=3, max_length=3)
    query: dict[str, Any]
    golden: dict[str, Any]


class CounterfactualInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["counterfactual_flip"] = "counterfactual_flip"
    instance_id: str
    world_base: dict[str, int | bool]
    world_mutant: dict[str, int | bool]
    query: dict[str, Any]
    golden: dict[str, Any]


class ObligationInventoryInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["obligation_inventory"] = "obligation_inventory"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    golden: dict[str, Any]


class SatUnsatInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["sat_unsat"] = "sat_unsat"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    golden: dict[str, Any]


class PairwiseInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_kind: Literal["pairwise"] = "pairwise"
    instance_id: str
    world: dict[str, int | bool] = Field(default_factory=dict)
    query_a: dict[str, int | bool] = Field(default_factory=dict)
    query_b: dict[str, int | bool] = Field(default_factory=dict)
    query: dict[str, Any]
    golden: dict[str, Any]


TemplateInstance = Annotated[
    Union[
        ScenarioInstance,
        DecisionQueryInstance,
        RuleAttributionInstance,
        BoundaryInstance,
        CounterfactualInstance,
        ObligationInventoryInstance,
        SatUnsatInstance,
        PairwiseInstance,
    ],
    Field(discriminator="template_kind"),
]

_template_adapter: TypeAdapter[TemplateInstance] = TypeAdapter(TemplateInstance)


class TemplateSuiteFile(BaseModel):
    """Single JSON file: suite header + instances array."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    suite_id: str = "default"
    instances: list[TemplateInstance]


def parse_instance_dict(raw: dict[str, Any]) -> TemplateInstance:
    return _template_adapter.validate_python(raw)


def load_suite_path(path: Path) -> TemplateSuiteFile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return TemplateSuiteFile.model_validate(data)


def sort_instances(instances: list[TemplateInstance]) -> list[TemplateInstance]:
    return sorted(instances, key=lambda x: x.instance_id)
