"""Chunk-level coverage checks for pivot WFM handoffs (global line_index vs forward PASS/REWRITE rows)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_AGENT3_FORWARD = frozenset({"PASS", "REWRITE"})


def read_handoff_lines_dicts(handoff_path: Path) -> list[Any]:
    """Return the ``lines`` array from a handoff JSON file (top-level or ``wfm_payload``)."""
    data = json.loads(handoff_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    return _lines_from_handoff_json(data)


def _lines_from_handoff_json(data: dict[str, Any]) -> list[Any]:
    raw = data.get("lines")
    if isinstance(raw, list):
        return raw
    wp = data.get("wfm_payload")
    if isinstance(wp, dict):
        inner = wp.get("lines")
        if isinstance(inner, list):
            return inner
    return []


@dataclass(frozen=True)
class ChunkCoverageReport:
    rule_index_start: int
    rule_index_end_exclusive: int
    ok: bool
    forward_count: int
    missing_indices: tuple[int, ...]
    duplicate_indices: tuple[int, ...]
    extra_indices: tuple[int, ...]
    blocking_rows: tuple[dict[str, Any], ...]


def analyze_chunk_handoff_coverage(
    handoff_path: Path,
    rule_index_start: int,
    rule_index_end_exclusive: int,
) -> ChunkCoverageReport:
    """Require each global index in ``[rule_index_start, rule_index_end_exclusive)`` as exactly one forward row."""
    expected = set(range(rule_index_start, rule_index_end_exclusive))
    blocking_list: list[dict[str, Any]] = []

    try:
        data = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ChunkCoverageReport(
            rule_index_start=rule_index_start,
            rule_index_end_exclusive=rule_index_end_exclusive,
            ok=False,
            forward_count=0,
            missing_indices=tuple(sorted(expected)),
            duplicate_indices=(),
            extra_indices=(),
            blocking_rows=(),
        )

    lines = _lines_from_handoff_json(data)
    seen_li: dict[int, int] = {}
    forward: set[int] = set()

    for row in lines:
        if not isinstance(row, dict):
            continue
        li_raw = row.get("line_index")
        try:
            li = int(li_raw)
        except (TypeError, ValueError):
            blocking_list.append({"line_index": li_raw, "reason": "bad_line_index"})
            continue
        seen_li[li] = seen_li.get(li, 0) + 1
        v = str(row.get("agent3_verdict") or "").strip().upper()
        nl = str(row.get("statement_nl") or "").strip()
        if v in _AGENT3_FORWARD and nl:
            forward.add(li)
        else:
            blocking_list.append(
                {
                    "line_index": li,
                    "agent3_verdict": v or "(missing)",
                    "statement_nl_preview": (nl[:120] + "…") if len(nl) > 120 else nl,
                }
            )

    duplicates = tuple(sorted(li for li, c in seen_li.items() if c > 1))
    extra = tuple(sorted(forward - expected))
    missing = tuple(sorted(expected - forward))
    ok = (
        len(missing) == 0
        and len(duplicates) == 0
        and len(extra) == 0
        and len(forward) == len(expected)
    )
    return ChunkCoverageReport(
        rule_index_start=rule_index_start,
        rule_index_end_exclusive=rule_index_end_exclusive,
        ok=ok,
        forward_count=len(forward),
        missing_indices=missing,
        duplicate_indices=duplicates,
        extra_indices=extra,
        blocking_rows=tuple(blocking_list[:40]),
    )


def patch_handoff_inject_missing_rules(
    handoff_path: Path,
    *,
    rule_index_start: int,
    rule_index_end_exclusive: int,
    all_rules: list[str],
) -> ChunkCoverageReport:
    """
    Ensure each index in the chunk has a forward row by injecting PASS rows (raw ``all_rules`` text).

    Returns the coverage report after patching (should be ``ok``).
    """
    cov = analyze_chunk_handoff_coverage(handoff_path, rule_index_start, rule_index_end_exclusive)
    if cov.duplicate_indices:
        raise ValueError(
            f"handoff has duplicate line_index values {cov.duplicate_indices}; fix or re-run WFM before inject."
        )

    data = json.loads(handoff_path.read_text(encoding="utf-8"))
    lines = _lines_from_handoff_json(data)
    by_idx: dict[int, dict[str, Any]] = {}

    for row in lines:
        if not isinstance(row, dict):
            continue
        try:
            li = int(row["line_index"])
        except (KeyError, TypeError, ValueError):
            continue
        by_idx[li] = dict(row)

    scope_note = "pivot_wfm_coverage_injection: raw source line retained (no Agent 2/3 PASS for this index)."
    for i in range(rule_index_start, rule_index_end_exclusive):
        if i < 0 or i >= len(all_rules):
            raise ValueError(f"cannot inject line_index {i}: outside all_rules len={len(all_rules)}")
        rl = all_rules[i].strip()
        if i not in by_idx or str(by_idx[i].get("agent3_verdict") or "").strip().upper() not in _AGENT3_FORWARD or not str(
            by_idx[i].get("statement_nl") or ""
        ).strip():
            by_idx[i] = {
                "line_index": i,
                "statement_nl": rl,
                "agent3_verdict": "PASS",
                "scope_report": scope_note,
                "diff_report": None,
                "agent2_line_text": f"{i + 1}. \"{rl}\"",
            }

    merged = [by_idx[k] for k in sorted(by_idx.keys())]
    if "lines" in data:
        data["lines"] = merged
    elif isinstance(data.get("wfm_payload"), dict):
        data["wfm_payload"]["lines"] = merged

    handoff_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return analyze_chunk_handoff_coverage(handoff_path, rule_index_start, rule_index_end_exclusive)


__all__ = [
    "ChunkCoverageReport",
    "analyze_chunk_handoff_coverage",
    "patch_handoff_inject_missing_rules",
    "read_handoff_lines_dicts",
]
