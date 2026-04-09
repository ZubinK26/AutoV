"""
M4 — automated registry resolve + validation (`development_plan_registry_stage_v1.md`).

Consumes ``LineSearchGapsResult`` (M3). No live LLM in default CI: inject ``llm_complete``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from registry_stage.line_driver import LineSearchGapsResult, authoritative_hits_context_nl
from registry_stage.llm.agents import LlmComplete, resolve_registry_nl_parsed
from registry_stage.models import StructuredGap
from registry_stage.registry_session import RegistrySession

RESOLVE_MODE = "automated_v1"
SCHEMA_RESOLVE_V1 = "resolve_v1"

PRIMARY_REASONS = frozenset({"NONE", "AMBIGUITY", "LOW_COVERAGE", "MISSING_REFERENCE", "OTHER"})
CONFIDENCE_TIERS = frozenset({"high", "medium", "low"})


def _active_entry_ids(session: RegistrySession) -> set[str]:
    return {eid for eid, e in session.entries.items() if e.status != "tombstoned"}


@dataclass
class ResolveAutomatedOutcome:
    """Result of ``run_automated_resolve`` (success or structured failure)."""

    success: bool
    registry_resolved_nl: str | None
    """Set only when validation passes (committed NL for formalizer)."""

    pre_resolved_nl: str | None
    """Phase 1: same as ``registry_resolved_nl`` on success; otherwise None."""

    registry_resolution_candidate_nl: str | None
    resolve_mode: str
    validation_outcome: str
    failure_reasons: list[str] = field(default_factory=list)
    llm_rationale_short: str | None = None
    raw_resolver_json: list[dict[str, Any]] = field(default_factory=list)
    attempts_used: int = 0


def _gaps_as_jsonable(gaps: tuple[StructuredGap, ...]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in gaps:
        d = asdict(g)
        d["domain_hints"] = list(d["domain_hints"])
        out.append(d)
    return out


def _validate_parsed(
    data: dict[str, Any],
    *,
    session: RegistrySession,
    authoritative_entry_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_RESOLVE_V1:
        errors.append(f"schema_version must be {SCHEMA_RESOLVE_V1!r}")

    cand = data.get("registry_resolution_candidate_nl")
    if not isinstance(cand, str) or not cand.strip():
        errors.append("registry_resolution_candidate_nl must be a non-empty string")

    pr = data.get("primary_review_reason")
    if pr not in PRIMARY_REASONS:
        errors.append(f"primary_review_reason must be one of {sorted(PRIMARY_REASONS)}")

    ct = data.get("confidence_tier")
    if ct not in CONFIDENCE_TIERS:
        errors.append(f"confidence_tier must be one of {sorted(CONFIDENCE_TIERS)}")

    nhr = data.get("needs_human_review")
    if not isinstance(nhr, bool):
        errors.append("needs_human_review must be a boolean")

    cited = data.get("cited_entry_ids")
    if not isinstance(cited, list):
        errors.append("cited_entry_ids must be a list")
    else:
        ids = [str(x) for x in cited]
        active = _active_entry_ids(session)
        for eid in ids:
            if eid not in active:
                errors.append(f"cited_entry_ids contains unknown or tombstoned id: {eid!r}")
        for eid in ids:
            if eid not in authoritative_entry_ids:
                errors.append(
                    f"cited_entry_ids must reference only authoritative hits: {eid!r} not in authoritative set"
                )

    # Automated success predicate (strict — dev plan)
    if not errors:
        if nhr is True:
            errors.append("needs_human_review must be false for auto-commit")
        if pr != "NONE":
            errors.append("primary_review_reason must be NONE for auto-commit")
        if ct != "high":
            errors.append("confidence_tier must be high for auto-commit")

    return errors


def run_automated_resolve(
    *,
    line_search_gaps: LineSearchGapsResult,
    session: RegistrySession,
    llm_complete: LlmComplete,
    max_validation_retries: int = 2,
) -> ResolveAutomatedOutcome:
    """
    Call the resolver LLM up to ``1 + max_validation_retries`` times (default 3).

    On success, ``registry_resolved_nl`` and ``pre_resolved_nl`` are both set to the
    validated candidate. On failure, ``failure_reasons`` summarize the last attempt.
    """
    raw_attempts: list[dict[str, Any]] = []
    feedback: str | None = None
    authoritative_ids = {h.entry_id for h in line_search_gaps.authoritative_hits}
    hits_context = authoritative_hits_context_nl(session, line_search_gaps.authoritative_hits)
    gap_list = list(line_search_gaps.gap_spans)
    struct_payload = _gaps_as_jsonable(line_search_gaps.structured_gaps)

    last_errors: list[str] = ["no attempt"]
    for attempt in range(max_validation_retries + 1):
        try:
            data = resolve_registry_nl_parsed(
                statement_nl=line_search_gaps.statement_nl,
                authoritative_hits_context=hits_context,
                gap_spans=gap_list,
                structured_gaps=struct_payload,
                llm_complete=llm_complete,
                validation_feedback=feedback,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            last_errors = [f"parse_or_model_error: {exc!s}"]
            raw_attempts.append({"_error": last_errors[0]})
            feedback = last_errors[0]
            continue

        raw_attempts.append(dict(data))
        errors = _validate_parsed(
            data,
            session=session,
            authoritative_entry_ids=authoritative_ids,
        )
        if not errors:
            cand = str(data["registry_resolution_candidate_nl"]).strip()
            rationale = data.get("llm_rationale_short")
            rshort = str(rationale).strip() if rationale is not None else None
            return ResolveAutomatedOutcome(
                success=True,
                registry_resolved_nl=cand,
                pre_resolved_nl=cand,
                registry_resolution_candidate_nl=cand,
                resolve_mode=RESOLVE_MODE,
                validation_outcome="passed",
                llm_rationale_short=rshort,
                raw_resolver_json=raw_attempts,
                attempts_used=attempt + 1,
            )
        last_errors = errors
        feedback = "; ".join(errors)

    return ResolveAutomatedOutcome(
        success=False,
        registry_resolved_nl=None,
        pre_resolved_nl=None,
        registry_resolution_candidate_nl=(
            str(raw_attempts[-1].get("registry_resolution_candidate_nl", "")).strip()
            if raw_attempts and isinstance(raw_attempts[-1], dict)
            else None
        ),
        resolve_mode=RESOLVE_MODE,
        validation_outcome="failed",
        failure_reasons=list(last_errors),
        llm_rationale_short=(
            str(raw_attempts[-1].get("llm_rationale_short") or "").strip() or None
            if raw_attempts and isinstance(raw_attempts[-1], dict)
            else None
        ),
        raw_resolver_json=raw_attempts,
        attempts_used=len(raw_attempts),
    )
