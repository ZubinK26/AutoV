"""LLM rewrite of an entire pivot WFM chunk when line coverage fails."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR, read_v1_policy_encodability_contract

from pivot_wfm.handoff_coverage import ChunkCoverageReport, read_handoff_lines_dicts


def _prompt_template() -> str:
    path = PROMPTS_DIR / "wfm_scope_rewrite.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing WFM scope prompt: {path}")
    return path.read_text(encoding="utf-8")


def handoff_line_summary(handoff_path: Path, *, max_rows: int = 30) -> str:
    if not handoff_path.is_file():
        return "(handoff missing)"
    raw_lines = read_handoff_lines_dicts(handoff_path)
    parts: list[str] = []
    for row in sorted(raw_lines, key=lambda x: int(x.get("line_index", 0)))[:max_rows]:
        if not isinstance(row, dict):
            continue
        li = row.get("line_index")
        v = row.get("agent3_verdict")
        nl = str(row.get("statement_nl") or "").replace("\n", " ").strip()
        if len(nl) > 100:
            nl = nl[:100] + "…"
        parts.append(f"- line_index={li} verdict={v!r} statement_nl={nl!r}")
    if len(raw_lines) > max_rows:
        parts.append(f"(… {len(raw_lines) - max_rows} more row(s) omitted)")
    return "\n".join(parts) if parts else "(no lines)"


def _coverage_summary(report: ChunkCoverageReport) -> str:
    bits = [
        f"ok={report.ok}",
        f"forward_count={report.forward_count}",
        f"missing_indices={list(report.missing_indices)}",
        f"duplicate_indices={list(report.duplicate_indices)}",
        f"extra_indices={list(report.extra_indices)}",
    ]
    if report.blocking_rows:
        bits.append("sample_blocking_rows:")
        for b in report.blocking_rows[:12]:
            bits.append(f"  {b}")
    return "\n".join(bits)


def run_wfm_chunk_scope_rewrite(
    chunk_rules: list[str],
    *,
    rule_index_start: int,
    rule_index_end_exclusive: int,
    file_label: str,
    coverage_report: ChunkCoverageReport,
    handoff_path: Path | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
) -> list[str]:
    """Return ``rewritten_rules`` with the same length as ``chunk_rules``."""
    n = len(chunk_rules)
    if n != rule_index_end_exclusive - rule_index_start:
        raise ValueError("chunk_rules length does not match index span")
    tmpl = _prompt_template().replace(
        "<<<V1_ENCODABILITY>>>", read_v1_policy_encodability_contract()
    )
    summary = _coverage_summary(coverage_report)
    ho_sum = handoff_line_summary(handoff_path, max_rows=30) if handoff_path else "(no handoff path)"
    rules_json = json.dumps(chunk_rules, ensure_ascii=False, indent=2)
    prompt = (
        tmpl.replace("<<<FILE_LABEL>>>", file_label)
        .replace("<<<CHUNK_INDEX_RANGE>>>", f"{rule_index_start}..{rule_index_end_exclusive - 1} inclusive")
        .replace("<<<CHUNK_RULE_COUNT>>>", str(n))
        .replace("<<<CHUNK_RULES_JSON_ARRAY>>>", rules_json)
        .replace("<<<COVERAGE_SUMMARY>>>", summary)
        .replace("<<<HANDOFF_LINE_SUMMARY>>>", ho_sum)
    )
    raw = llm(prompt)
    data = parse_json_object(raw)
    out = data.get("rewritten_rules")
    if not isinstance(out, list):
        raise ValueError("wfm_scope_rewrite: rewritten_rules must be a list")
    cleaned = [str(x).strip() for x in out]
    if len(cleaned) != n:
        raise ValueError(f"wfm_scope_rewrite: expected {n} rules, got {len(cleaned)}")
    if any(not x for x in cleaned):
        raise ValueError("wfm_scope_rewrite: empty rewritten rule")
    return cleaned


__all__ = ["run_wfm_chunk_scope_rewrite", "handoff_line_summary"]
