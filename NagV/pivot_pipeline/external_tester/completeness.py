"""Deterministic validation of external fill payloads."""

from __future__ import annotations

from pivot_pipeline.external_tester.schemas import ExternalWorldFillV1
from pivot_pipeline.ir import MetaScheme


def check_completeness(fill: ExternalWorldFillV1, meta: MetaScheme) -> list[str]:
    """Return human-readable errors (empty if ok)."""
    errors: list[str] = []
    expected = sorted(meta.variable_sorts.keys())
    if not expected:
        errors.append("meta.variable_sorts is empty")
        return errors

    got = sorted(a.variable for a in fill.assignments)
    if got != expected:
        missing = sorted(set(expected) - set(got))
        extra = sorted(set(got) - set(expected))
        if missing:
            errors.append(f"missing assignments for: {', '.join(missing)}")
        if extra:
            errors.append(f"unexpected assignment variables: {', '.join(extra)}")

    for a in fill.assignments:
        exp_sort = meta.variable_sorts.get(a.variable)
        if exp_sort and a.sort != exp_sort:
            errors.append(f"{a.variable}: sort {a.sort!r} != catalog {exp_sort!r}")

    if fill.template_kind == "scenario":
        if fill.query is not None:
            errors.append("scenario fill must not include query")
        if not isinstance(fill.golden.get("sat"), bool):
            errors.append("scenario golden must have boolean sat")
    elif fill.template_kind == "decision_query":
        q = fill.query or {}
        if q.get("decision_metric") != "rule":
            errors.append("decision_query requires query.decision_metric == 'rule'")
        rid = q.get("rule_id")
        if not isinstance(rid, str) or not rid.strip():
            errors.append("decision_query requires query.rule_id")
        d = fill.golden.get("decision")
        if d not in ("satisfied", "unsatisfied"):
            errors.append("golden.decision must be satisfied|unsatisfied")

    return errors


__all__ = ["check_completeness"]
