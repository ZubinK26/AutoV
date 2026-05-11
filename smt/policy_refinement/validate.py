"""Validate assessor / implementer JSON (policy refinement v1 schemas)."""

from __future__ import annotations

import re
from typing import Any


_ASSESSMENT_SV = "policy_refinement_assessment_v1"
_IMPLEMENTATION_SV = "policy_refinement_implementation_v1"


def validate_assessment(data: dict[str, Any], *, max_recommendations: int) -> list[str]:
    errs: list[str] = []
    if data.get("schema_version") != _ASSESSMENT_SV:
        errs.append(f"expected schema_version {_ASSESSMENT_SV!r}")
    recs = data.get("recommendations")
    if not isinstance(recs, list):
        errs.append("recommendations must be a list")
        return errs
    if len(recs) > max_recommendations:
        errs.append(f"too many recommendations ({len(recs)} > {max_recommendations})")
    seen: set[str] = set()
    for i, r in enumerate(recs):
        if not isinstance(r, dict):
            errs.append(f"recommendations[{i}] not an object")
            continue
        rid = r.get("rec_id")
        if not rid or not isinstance(rid, str):
            errs.append(f"recommendations[{i}].rec_id missing")
        elif rid in seen:
            errs.append(f"duplicate rec_id {rid!r}")
        else:
            seen.add(rid)
        for key in ("severity", "issue_type", "description", "suggested_remediation"):
            if key not in r or not isinstance(r[key], str):
                errs.append(f"recommendations[{i}].{key} missing or not a string")
        ev = r.get("nl_evidence")
        if not isinstance(ev, dict):
            errs.append(f"recommendations[{i}].nl_evidence must be an object")
        else:
            nums = ev.get("line_numbers")
            if nums is not None and not isinstance(nums, list):
                errs.append(f"recommendations[{i}].nl_evidence.line_numbers must be a list or absent")
        pe = r.get("policy_evidence")
        if not isinstance(pe, dict):
            errs.append(f"recommendations[{i}].policy_evidence must be an object")
        else:
            has = False
            if pe.get("rule_id"):
                has = True
            lr = pe.get("line_range_1based")
            if isinstance(lr, list) and len(lr) == 2:
                has = True
            if pe.get("symbol"):
                has = True
            if not has:
                errs.append(f"recommendations[{i}].policy_evidence needs rule_id, line_range_1based, or symbol")
    return errs


def validate_implementation(
    data: dict[str, Any],
    *,
    allowed_rec_ids: set[str],
    policy_text: str,
) -> list[str]:
    errs: list[str] = []
    if data.get("schema_version") != _IMPLEMENTATION_SV:
        errs.append(f"expected schema_version {_IMPLEMENTATION_SV!r}")
    full = data.get("policy_smt2_full_text")
    if not full or not isinstance(full, str) or not full.strip():
        errs.append("policy_smt2_full_text missing or empty")
    addr = data.get("rec_ids_addressed")
    if not isinstance(addr, list) or not all(isinstance(x, str) for x in addr):
        errs.append("rec_ids_addressed must be a list of strings")
    elif addr:
        for rid in addr:
            if rid not in allowed_rec_ids:
                errs.append(f"rec_ids_addressed contains unknown rec_id {rid!r}")
        for rid in addr:
            if not _policy_has_refine_marker(policy_text, rid):
                errs.append(f"no ; --- REFINE rec_id={rid} marker in policy_smt2_full_text")
    skipped = data.get("rec_ids_skipped")
    if skipped is not None and (not isinstance(skipped, list) or not all(isinstance(x, str) for x in skipped)):
        errs.append("rec_ids_skipped must be a list of strings or absent")
    return errs


def _policy_has_refine_marker(policy_text: str, rec_id: str) -> bool:
    return bool(re.search(rf"^; --- REFINE rec_id={re.escape(rec_id)}\b", policy_text, re.MULTILINE))


def policy_rule_ids_in_text(policy_text: str) -> set[str]:
    out: set[str] = set()
    for m in re.finditer(r"^; Rule: (?P<rid>\S+)\s+\|\s+Line:", policy_text, re.MULTILINE):
        out.add(m.group("rid"))
    return out


def validate_assessor_policy_refs(assessment: dict[str, Any], policy_text: str) -> list[str]:
    """Warn-level validation: rule_id in policy if present."""
    errs: list[str] = []
    known = policy_rule_ids_in_text(policy_text)
    nlines = policy_text.count("\n") + (1 if policy_text else 0)
    for r in assessment.get("recommendations") or []:
        if not isinstance(r, dict):
            continue
        pe = r.get("policy_evidence")
        if not isinstance(pe, dict):
            continue
        rid = pe.get("rule_id")
        if rid and isinstance(rid, str) and rid not in known:
            errs.append(f"{r.get('rec_id')}: policy_evidence.rule_id {rid!r} not found in policy")
        lr = pe.get("line_range_1based")
        if isinstance(lr, list) and len(lr) == 2:
            a, b = lr[0], lr[1]
            if isinstance(a, int) and isinstance(b, int):
                if a < 1 or b < a or b > nlines:
                    errs.append(f"{r.get('rec_id')}: line_range_1based {lr} out of range (policy lines={nlines})")
    return errs
