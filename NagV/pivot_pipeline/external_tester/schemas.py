"""Pydantic schemas for external world tester (schema_version 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExternalSourceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    source_id: str
    line_count: int
    lines: list[str]
    case_scope: dict[str, int | bool] = Field(
        default_factory=dict,
        description="Optional evaluation scope: grounded variable → value (policy literals as harvested int ids).",
    )

    @model_validator(mode="after")
    def _line_count_matches(self) -> ExternalSourceEnvelope:
        if self.line_count != len(self.lines):
            raise ValueError(f"line_count {self.line_count} != len(lines) {len(self.lines)}")
        return self


class ProvenanceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_numbers: list[int] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)


class VariableAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    sort: Literal["int", "bool"]
    status: Literal["present", "inferred", "not_found"]
    value: int | bool | None = None
    provenance: ProvenanceRef = Field(default_factory=ProvenanceRef)
    rationale: str = ""

    @model_validator(mode="after")
    def _value_for_status(self) -> VariableAssignment:
        if self.status == "not_found":
            if self.value is not None:
                raise ValueError(f"{self.variable}: not_found must omit value")
            if self.provenance.line_numbers or self.provenance.quotes:
                raise ValueError(f"{self.variable}: not_found must have empty provenance")
            return self
        if self.value is None:
            raise ValueError(f"{self.variable}: {self.status} requires value")
        if self.sort == "bool" and not isinstance(self.value, bool):
            raise ValueError(f"{self.variable}: sort bool requires bool value")
        if self.sort == "int" and not isinstance(self.value, int):
            raise ValueError(f"{self.variable}: sort int requires int value")
        if not self.provenance.line_numbers:
            raise ValueError(f"{self.variable}: {self.status} requires provenance.line_numbers")
        return self


class ExternalWorldFillV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    instance_id: str
    template_kind: Literal["decision_query", "scenario"] = "scenario"
    query: dict[str, Any] | None = None
    golden: dict[str, Any]
    assignments: list[VariableAssignment]

    @model_validator(mode="after")
    def _template_kind_constraints(self) -> ExternalWorldFillV1:
        if self.template_kind == "scenario":
            if self.query is not None:
                raise ValueError("scenario fill must not include query")
            if not isinstance(self.golden.get("sat"), bool):
                raise ValueError("scenario golden must have boolean sat")
        elif self.template_kind == "decision_query":
            if self.query is None:
                raise ValueError("decision_query fill requires query")
            q = self.query
            if q.get("decision_metric") != "rule":
                raise ValueError("decision_query requires query.decision_metric == 'rule'")
            rid = q.get("rule_id")
            if not isinstance(rid, str) or not rid.strip():
                raise ValueError("decision_query requires query.rule_id")
            if self.golden.get("decision") not in ("satisfied", "unsatisfied"):
                raise ValueError("decision_query golden.decision must be satisfied|unsatisfied")
        return self


class FieldProvenanceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    verdict: Literal["supported", "unsupported", "derivable", "not_applicable"]
    notes: str = ""


class ExternalWorldFillBatchV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    batch_id: str
    variables_requested: list[str]
    assignments: list[VariableAssignment]


class FlaggedVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    reason: str = ""


class ExternalCompletenessReviewV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    verdict: Literal["PASS", "FAIL"]
    flagged_variables: list[FlaggedVariable] = Field(default_factory=list)


class ExternalProvenanceReviewV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    verdict: Literal["PASS", "FAIL"]
    field_reviews: list[FieldProvenanceReview] = Field(default_factory=list)
    blocking_variables: list[str] = Field(default_factory=list)


class StatedAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    sort: Literal["int", "bool"]
    status: Literal["present", "inferred"]
    value: int | bool
    provenance: ProvenanceRef
    rationale: str = ""
    tier: Literal["grounded"] = "grounded"

    @model_validator(mode="after")
    def _value_sort(self) -> StatedAssignment:
        if self.sort == "bool" and not isinstance(self.value, bool):
            raise ValueError(f"{self.variable}: sort bool requires bool value")
        if self.sort == "int" and not isinstance(self.value, int):
            raise ValueError(f"{self.variable}: sort int requires int value")
        if not self.provenance.line_numbers:
            raise ValueError(f"{self.variable}: stated requires provenance.line_numbers")
        return self


class DerivedAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    sort: Literal["int", "bool"]
    status: Literal["derived"] = "derived"
    value: int | bool
    source: Literal["z3_witness", "llm_glossary", "strict_eval"] = "z3_witness"
    rationale: str = ""

    @model_validator(mode="after")
    def _value_sort(self) -> DerivedAssignment:
        if self.sort == "bool" and not isinstance(self.value, bool):
            raise ValueError(f"{self.variable}: sort bool requires bool value")
        if self.sort == "int" and not isinstance(self.value, int):
            raise ValueError(f"{self.variable}: sort int requires int value")
        return self


class PolicyCaseWorldV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    instance_id: str
    stated: list[StatedAssignment] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    derived: list[DerivedAssignment] = Field(default_factory=list)
    coverage: dict[str, int] = Field(default_factory=dict)


class PolicyQueryResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    query_mode: Literal["strict", "lenient"] = "strict"
    z3_status: Literal["sat", "unsat", "unknown"]
    compatibility: Literal["compatible", "incompatible", "unknown"]
    defaulted_variables: list[str] = Field(default_factory=list)
    default_policy: str = "cwa_pessimistic_v1"
    witness_unknown: dict[str, int | bool] = Field(default_factory=dict)
    witness_derived: dict[str, int | bool] = Field(default_factory=dict)
    witness_note: str = ""


class PolicyQueryAddendumV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    strict: PolicyQueryResultV1
    lenient: PolicyQueryResultV1 | None = None
    summary: str = ""
    strict_incompatible_lenient_compatible: bool | None = None


class UnsatCoreRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    linearized: str = ""


class PolicyCaseExplanationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    compatibility: Literal["compatible", "incompatible", "unknown"]
    unsat_core_rules: list[UnsatCoreRule] = Field(default_factory=list)
    witness: dict[str, int | bool] | None = None
    defaulted_variables: list[str] = Field(default_factory=list)
    note: str = ""


class PolicyCaseReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    instance_id: str
    outcome: Literal[
        "complete",
        "blocked_insufficient_evidence",
        "blocked_provenance",
        "blocked_query",
        "error",
    ]
    provenance_verdict: str | None = None
    pathway_id: str = "compiled_default"
    tier1_complete: bool | None = None
    sufficiency_report_path: str | None = None
    tier_addendum_path: str | None = None
    tier_addendum_summary: str | None = None
    compatibility: Literal["compatible", "incompatible", "unknown"] | None = None
    z3_status: Literal["sat", "unsat", "unknown"] | None = None
    world_coverage: dict[str, int] = Field(default_factory=dict)
    explanation_path: str | None = None
    narrative_path: str | None = None
    defaulted_at_query: list[str] = Field(default_factory=list)
    lenient_compatibility: Literal["compatible", "incompatible", "unknown"] | None = None
    lenient_z3_status: Literal["sat", "unsat", "unknown"] | None = None
    query_addendum_path: str | None = None
    dual_query_summary: str | None = None
    error: str | None = None
    link_warnings: list[str] = Field(default_factory=list)
    strict_incompatible_lenient_compatible: bool | None = None


def load_source_path(path: Path) -> ExternalSourceEnvelope:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        return ExternalSourceEnvelope.model_validate(data)
    from pivot_pipeline.external_tester.source_numbering import raw_text_to_envelope

    return raw_text_to_envelope(text, source_id=path.stem)


__all__ = [
    "DerivedAssignment",
    "ExternalCompletenessReviewV1",
    "ExternalProvenanceReviewV1",
    "ExternalSourceEnvelope",
    "ExternalWorldFillBatchV1",
    "ExternalWorldFillV1",
    "FieldProvenanceReview",
    "FlaggedVariable",
    "PolicyCaseExplanationV1",
    "PolicyCaseReportV1",
    "PolicyCaseWorldV1",
    "PolicyQueryAddendumV1",
    "PolicyQueryResultV1",
    "ProvenanceRef",
    "StatedAssignment",
    "UnsatCoreRule",
    "VariableAssignment",
    "load_source_path",
]
