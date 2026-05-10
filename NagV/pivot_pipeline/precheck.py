"""Lightweight coverage checks before (or instead of) LLM critic."""

from __future__ import annotations

import re
from pathlib import Path

from pivot_pipeline.ir import ConstantRelational, MetaScheme


def extract_numeric_constants_from_nl(nl_text: str) -> set[str]:
    """Digits / currency-like tokens for coarse cross-check."""
    found: set[str] = set()
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", nl_text):
        found.add(m.group(0))
    return found


def extract_numeric_constants_from_meta(meta: MetaScheme) -> set[str]:
    found: set[str] = set()
    for r in meta.rules:
        if isinstance(r, ConstantRelational) and isinstance(r.constant_value, (int, float)):
            found.add(str(int(r.constant_value)) if isinstance(r.constant_value, float) and r.constant_value == int(r.constant_value) else str(r.constant_value))
    return found


def run_precheck(*, nl_path: Path, meta: MetaScheme) -> tuple[bool, list[str]]:
    """Return (ok, issues)."""
    issues: list[str] = []
    nl_text = nl_path.read_text(encoding="utf-8")
    rule_ids = {r.rule_id for r in meta.rules}
    for pw in meta.evaluation_pathways:
        for rid in pw.must_satisfy_all:
            if rid not in rule_ids:
                issues.append(f"pathway {pw.pathway_id} references unknown rule {rid!r}")
    # Optional: numeric heuristic (NL digit must appear somewhere in meta — very weak)
    nl_nums = extract_numeric_constants_from_nl(nl_text)
    meta_nums = extract_numeric_constants_from_meta(meta)
    for n in sorted(meta_nums):
        if n not in nl_nums and n not in nl_text:
            issues.append(f"constant {n!r} in meta not found in source NL (heuristic)")
    return len(issues) == 0, issues
