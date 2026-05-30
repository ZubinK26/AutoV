"""Aggregate reviewer field verdicts into PASS/FAIL."""

from __future__ import annotations

from pivot_pipeline.external_tester.schemas import (
    ExternalProvenanceReviewV1,
    ExternalWorldFillV1,
    FieldProvenanceReview,
)


def aggregate_review(
    fill: ExternalWorldFillV1,
    field_reviews: list[FieldProvenanceReview],
) -> ExternalProvenanceReviewV1:
    by_var = {fr.variable: fr for fr in field_reviews}
    blocking: list[str] = []
    merged: list[FieldProvenanceReview] = []

    for a in fill.assignments:
        fr = by_var.get(a.variable)
        if fr is None:
            merged.append(
                FieldProvenanceReview(
                    variable=a.variable,
                    verdict="unsupported",
                    notes="missing field review",
                )
            )
            if a.status != "not_found":
                blocking.append(a.variable)
            continue
        merged.append(fr)
        if a.status == "not_found":
            if fr.verdict not in ("not_applicable", "supported", "derivable"):
                blocking.append(a.variable)
            continue
        if fr.verdict == "unsupported":
            blocking.append(a.variable)

    verdict = "PASS" if not blocking else "FAIL"
    return ExternalProvenanceReviewV1(
        verdict=verdict,
        field_reviews=merged,
        blocking_variables=sorted(set(blocking)),
    )


__all__ = ["aggregate_review"]
