"""Tier-3 speculative LLM fill for missing pathway variables."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pivot_pipeline.external_tester.api_retry import call_with_api_retries
from pivot_pipeline.external_tester.llm import external_llm_complete
from pivot_pipeline.external_tester.pathway_sufficiency import PathwaySufficiencyReportV1
from pivot_pipeline.external_tester.policy_query import run_policy_query
from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    PolicyCaseWorldV1,
    PolicyQueryResultV1,
    ProvenanceRef,
    StatedAssignment,
)
from pivot_pipeline.external_tester.variable_tiers import Tier
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.paths import PROMPTS_DIR


class ProvenanceAuditV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_numbers: list[int] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    rationale: str = ""


class SpeculativeSuggestionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    sort: Literal["int", "bool"]
    value: int | bool
    confidence: Literal["low", "medium", "high"] = "low"
    provenance_audit: ProvenanceAuditV1 = Field(default_factory=ProvenanceAuditV1)
    basis: str = ""


class SpeculativeFillV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    suggestions: list[SpeculativeSuggestionV1] = Field(default_factory=list)
    tier3_query: PolicyQueryResultV1 | None = None
    skipped: bool = False
    skip_reason: str = ""


def tier3_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    raw = os.getenv("PIVOT_CASE_TIER3", "on").strip().lower()
    return raw not in ("off", "false", "0", "no")


def _numbered_source(source: ExternalSourceEnvelope) -> str:
    """Format envelope lines (list[str]) as L1: ... like phase-1 fill prompts."""
    return "\n".join(f"L{i}: {text}" for i, text in enumerate(source.lines, start=1))


def _build_speculative_prompt(
    *,
    source: ExternalSourceEnvelope,
    missing: list[str],
    sorts: dict[str, str],
) -> str:
    template = (PROMPTS_DIR / "external_case_speculative_fill.md").read_text(encoding="utf-8")
    catalog = "\n".join(f"- `{n}` ({sorts.get(n, '?')})" for n in missing)
    user = (
        f"{template}\n\n---\n\n"
        f"## Missing variables\n{catalog}\n\n"
        f"## Source\n```\n{_numbered_source(source)}\n```\n"
    )
    return user


def run_tier3_speculative(
    *,
    work_dir: Any,
    source: ExternalSourceEnvelope,
    world: PolicyCaseWorldV1,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    tiers: dict[str, Tier],
    sufficiency: PathwaySufficiencyReportV1,
    base_world: PolicyCaseWorldV1 | None = None,
) -> tuple[SpeculativeFillV1, PolicyCaseWorldV1]:
    """LLM suggestions for missing vars; strict query on speculative world."""
    _ = work_dir, rules, tiers
    missing = [m.variable for m in sufficiency.missing]
    if not missing:
        return SpeculativeFillV1(skipped=True, skip_reason="no_missing_variables"), world

    if not tier3_enabled():
        return SpeculativeFillV1(skipped=True, skip_reason="PIVOT_CASE_TIER3=off"), world

    sorts = dict(meta.variable_sorts)
    prompt = _build_speculative_prompt(source=source, missing=missing, sorts=sorts)
    suggestions: list[SpeculativeSuggestionV1] = []
    skip_reason = ""

    try:
        raw = call_with_api_retries(
            lambda: external_llm_complete(prompt, stage="fill"),
            label="tier3_speculative",
        )
        data = parse_json_object(raw)
        fill = SpeculativeFillV1.model_validate(data)
        allowed = set(missing)
        suggestions = [s for s in fill.suggestions if s.variable in allowed]
    except (ValidationError, ValueError, RuntimeError, OSError) as e:
        skip_reason = f"{type(e).__name__}: {e}"

    seed = base_world or world
    speculative_stated = list(seed.stated)
    stated_names = {s.variable for s in speculative_stated}
    unknown = list(seed.unknown)
    for s in suggestions:
        if s.variable in stated_names:
            continue
        speculative_stated.append(
            StatedAssignment(
                variable=s.variable,
                sort=s.sort,
                status="inferred",
                value=s.value,
                provenance=ProvenanceRef(
                    line_numbers=list(s.provenance_audit.line_numbers) or [0],
                    quotes=list(s.provenance_audit.quotes) or ["tier3:speculative"],
                ),
                rationale=s.provenance_audit.rationale or "tier-3 speculative",
            )
        )
        stated_names.add(s.variable)
        if s.variable in unknown:
            unknown.remove(s.variable)

    spec_world = seed.model_copy(update={"stated": speculative_stated, "unknown": unknown})

    tier3_query: PolicyQueryResultV1 | None = None
    if suggestions:
        try:
            tier3_query, _ = run_policy_query(meta, spec_world, unknown_policy="block")
        except ValueError:
            tier3_query = PolicyQueryResultV1(
                query_mode="strict",
                z3_status="unknown",
                compatibility="unknown",
                defaulted_variables=[],
                default_policy="tier3_blocked_incomplete",
            )

    report = SpeculativeFillV1(
        suggestions=suggestions,
        tier3_query=tier3_query,
        skipped=not suggestions and bool(skip_reason),
        skip_reason=skip_reason,
    )
    return report, spec_world


__all__ = [
    "SpeculativeFillV1",
    "SpeculativeSuggestionV1",
    "run_tier3_speculative",
    "tier3_enabled",
]
