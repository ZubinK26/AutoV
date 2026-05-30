"""Trust: provenance review on stated fields only."""

from __future__ import annotations

import os

from pivot_pipeline.external_tester.review_agent import run_review_agent
from pivot_pipeline.external_tester.schemas import (
    ExternalProvenanceReviewV1,
    ExternalSourceEnvelope,
    ExternalWorldFillV1,
    PolicyCaseWorldV1,
    VariableAssignment,
)
from pivot_pipeline.ir import MetaScheme


def _provenance_max_rounds() -> int:
    raw = os.getenv(
        "PIVOT_CASE_PROVENANCE_MAX_ROUNDS",
        os.getenv("PIVOT_EXTERNAL_REVIEW_MAX_ROUNDS", "2"),
    ).strip()
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return 2


def world_to_review_fill(world: PolicyCaseWorldV1) -> ExternalWorldFillV1:
    """Minimal fill envelope for blind provenance review (stated only)."""
    assignments: list[VariableAssignment] = []
    for s in world.stated:
        assignments.append(
            VariableAssignment(
                variable=s.variable,
                sort=s.sort,
                status=s.status,
                value=s.value,
                provenance=s.provenance,
                rationale=s.rationale,
            )
        )
    return ExternalWorldFillV1(
        instance_id=world.instance_id,
        template_kind="scenario",
        golden={"sat": True},
        assignments=assignments,
    )


def run_trust_review(
    *,
    work_dir,
    source: ExternalSourceEnvelope,
    world: PolicyCaseWorldV1,
    meta: MetaScheme,
) -> ExternalProvenanceReviewV1:
    fill = world_to_review_fill(world)
    return run_review_agent(work_dir=work_dir, source=source, fill=fill, meta=meta)


__all__ = [
    "_provenance_max_rounds",
    "run_trust_review",
    "world_to_review_fill",
]
