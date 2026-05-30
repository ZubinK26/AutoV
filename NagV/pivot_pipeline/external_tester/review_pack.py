"""Blind provenance review packs (cited lines only)."""

from __future__ import annotations

import json

from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    ExternalWorldFillV1,
    VariableAssignment,
)

_QUOTE_CAP = 800


def _format_line_block(line_no: int, text: str) -> str:
    return f"L{line_no}: {text}"


def cited_lines_for_assignment(source: ExternalSourceEnvelope, assignment: VariableAssignment) -> list[str]:
    blocks: list[str] = []
    for ln in assignment.provenance.line_numbers:
        if ln < 1 or ln > source.line_count:
            continue
        blocks.append(_format_line_block(ln, source.lines[ln - 1]))
    return blocks


def build_field_review_section(source: ExternalSourceEnvelope, assignment: VariableAssignment) -> str:
    """One field block for reviewer — no uncited source lines."""
    lines = [
        f"## Field: {assignment.variable}",
        f"status: {assignment.status}",
        f"sort: {assignment.sort}",
    ]
    if assignment.value is not None:
        lines.append(f"claimed_value: {json_repr_scalar(assignment.value)}")
    lines.append(f"rationale: {assignment.rationale}")
    if assignment.status == "not_found":
        lines.append("(no source lines — reviewer verdict should be not_applicable)")
        return "\n".join(lines)

    lines.append("cited_source_lines_only:")
    for block in cited_lines_for_assignment(source, assignment):
        lines.append(block)
    if assignment.provenance.quotes:
        lines.append("agent_quotes:")
        for q in assignment.provenance.quotes:
            t = q if len(q) <= _QUOTE_CAP else q[:_QUOTE_CAP] + "..."
            lines.append(f"  - {t!r}")
    return "\n".join(lines)


def json_repr_scalar(v: int | bool) -> str:
    return json.dumps(v)


def build_blind_review_user_message(
    source: ExternalSourceEnvelope,
    fill: ExternalWorldFillV1,
    *,
    catalog_one_liners: dict[str, str] | None = None,
) -> str:
    """Full reviewer user message: field sections only, no full document, no golden."""
    parts = [
        "Review each field below. You only see cited source lines per field.",
        "Verdict per field: supported | unsupported | derivable | not_applicable (not_found only).",
        "",
    ]
    if catalog_one_liners:
        parts.append("### Variable hints (sort only)")
        for name in sorted(catalog_one_liners.keys()):
            if name in {a.variable for a in fill.assignments}:
                parts.append(f"- {name}: {catalog_one_liners[name]}")
        parts.append("")

    for a in fill.assignments:
        parts.append(build_field_review_section(source, a))
        parts.append("")
    return "\n".join(parts).strip()


__all__ = [
    "build_blind_review_user_message",
    "build_field_review_section",
    "cited_lines_for_assignment",
]
