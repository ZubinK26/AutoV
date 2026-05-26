"""Expansion-preserving linearization for LLM assessment (tester, cross-critic, critic digest)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from pivot_pipeline.ir_vnext import VNEXT_TEMPLATE_CLASSES
from pivot_pipeline.linearize_rules import format_condition, linearize_rule_line


def rules_contain_vnext(rules: list[dict[str, Any]]) -> bool:
    return any(str(r.get("template_class")) in VNEXT_TEMPLATE_CLASSES for r in rules)


def _linearize_vnext(rule: Mapping[str, Any]) -> list[str]:
    rid = rule.get("rule_id", "?")
    tc = str(rule.get("template_class", "?"))
    lines: list[str] = [f"[{rid}] {tc}"]

    if tc == "INT_RANGE":
        lines.append(
            f"  range: {rule['variable']} in [{rule['lo']}, {rule['hi']}] inclusive"
            f" | yields {rule.get('yields', 'SATISFIED')}"
        )
    elif tc == "DECISION_TABLE_ROW":
        lines.append(f"  IF {format_condition(rule['trigger_condition'])}")
        lines.append(f"  THEN {format_condition(rule['required_condition'])}")
    elif tc == "TABLE_BLOCK":
        tid = rule.get("table_id") or rid
        lines.append(f"  table_id: {tid} | rows: {len(rule.get('rows') or [])}")
        for idx, row in enumerate(rule.get("rows") or []):
            lines.append(f"  row {idx + 1}: IF {format_condition(row['trigger_condition'])}")
            lines.append(f"         THEN {format_condition(row['required_condition'])}")
    elif tc == "BOUNDED_FORALL":
        domain = rule.get("domain") or []
        dom_s = ", ".join(json.dumps(v, ensure_ascii=False) for v in domain)
        lines.append(f"  forall {rule['iter_variable']} in [{dom_s}]:")
        lines.append(f"    {format_condition(rule['required_condition'])}")
    elif tc == "K_OF_N":
        clauses = rule.get("clauses") or []
        k = rule.get("k")
        lines[0] = f"[{rid}] K_OF_N at_least k={k} of n={len(clauses)}"
        lines.append("  clauses:")
        for idx, c in enumerate(clauses):
            lines.append(f"    clause {idx + 1}: {format_condition(c)}")
    elif tc == "EXHAUSTIVE_SWITCH":
        disc = rule["discriminant_variable"]
        lines.append(f"  switch on {disc}:")
        for idx, case in enumerate(rule.get("cases") or []):
            lines.append(
                f"    case {json.dumps(case['value'], ensure_ascii=False)}: "
                f"{format_condition(case['consequence'])}"
            )
        if rule.get("default_consequence") is not None:
            lines.append(f"    default: {format_condition(rule['default_consequence'])}")
    elif tc == "DEFINED_AS":
        lines.append(f"  variable {rule['variable']} must satisfy:")
        lines.append(f"    {format_condition(rule['definition'])}")
    elif tc == "SUM_THRESHOLD":
        terms = rule.get("terms") or []
        op = rule.get("relational_operator", "")
        lim = rule.get("limit", "")
        parts = []
        for t in terms:
            c = t.get("coeff", 1)
            v = t.get("variable", "")
            parts.append(f"{c}*{v}" if c != 1 else v)
        sum_s = " + ".join(parts) if parts else "(empty)"
        lines.append(f"  sum: {sum_s} {op} {lim} | yields {rule.get('yields', 'SATISFIED')}")
        for idx, t in enumerate(terms):
            lines.append(f"    term {idx + 1}: coeff={t.get('coeff', 1)} variable={t.get('variable', '')}")
    else:
        lines.append(f"  (unknown vNext template) {json.dumps(rule, ensure_ascii=False)}")

    return lines


def build_assessment_linearized(rules: list[dict[str, Any]]) -> str:
    """
    Linearize rules for LLM gates: vNext templates stay as-authored; core templates use standard lines.
    """
    header = (
        "LINEARIZED MODEL (assessment view; expansion templates shown pre-lowering)",
        "",
    )
    blocks: list[str] = list(header)
    for r in rules:
        tc = str(r.get("template_class", ""))
        if tc in VNEXT_TEMPLATE_CLASSES:
            blocks.extend(_linearize_vnext(r))
        else:
            blocks.append(linearize_rule_line(r))
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def assessment_linearized_artifact_path(work_dir: Path) -> Path:
    return work_dir / "linearized_model_for_assessment.txt"


def expansion_assessment_digest_path(work_dir: Path) -> Path:
    return work_dir / "expansion_assessment_digest.md"


def build_and_write_assessment_artifacts(
    *,
    work_dir: Path,
    rules: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
) -> str:
    """
    Write assessment linearization for tester/cross-critic and optional expansion digest for critic.
    """
    text = build_assessment_linearized(rules)
    assessment_path = assessment_linearized_artifact_path(work_dir)
    assessment_path.write_text(text, encoding="utf-8")
    cross_path = work_dir / "linearized_model_for_cross_critic.txt"
    cross_path.write_text(text, encoding="utf-8")
    if summary is not None:
        summary["assessment_linearized"] = str(assessment_path.resolve())
        summary["linearized_model_for_cross_critic"] = str(cross_path.resolve())
        summary["assessment_view_used"] = True
    if rules_contain_vnext(rules):
        digest = (
            "# Expansion assessment digest (pre-lowering rules)\n\n"
            "Pivot critic: use this appendix for vNext template shape. "
            "Synthetic English reflects lowered core IR for Z3.\n\n"
            + text
        )
        dpath = expansion_assessment_digest_path(work_dir)
        dpath.write_text(digest, encoding="utf-8")
        if summary is not None:
            summary["expansion_assessment_digest"] = str(dpath.resolve())
    return text


__all__ = [
    "assessment_linearized_artifact_path",
    "build_and_write_assessment_artifacts",
    "build_assessment_linearized",
    "expansion_assessment_digest_path",
    "rules_contain_vnext",
]
