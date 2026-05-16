"""LLM rewrite of an entire pivot WFM chunk when line coverage fails."""

from __future__ import annotations

import json
import re
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


NOTE_LINE_RE = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")


def parse_rule_numbers_to_local_indices(
    *,
    chunk_start_0: int,
    chunk_len: int,
    spec: str,
) -> frozenset[int] | None:
    """
    Parse human rule numbers as shown in the CLI (1-based ordinal = chunk_start_0 + local + 1).

    ``spec`` empty after strip → ``None`` (full chunk regen, no pinning).
    """
    s = (spec or "").strip()
    if not s:
        return None
    out: set[int] = set()
    for raw_part in s.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                lo = int(a.strip())
                hi = int(b.strip())
            except ValueError as e:
                raise ValueError(f"invalid range {part!r}") from e
            if lo > hi:
                lo, hi = hi, lo
            rng = range(lo, hi + 1)
        else:
            try:
                rng = [int(part)]
            except ValueError as e:
                raise ValueError(f"invalid rule number {part!r}") from e
        for G in rng:
            j = G - chunk_start_0 - 1
            if j < 0 or j >= chunk_len:
                raise ValueError(
                    f"rule number {G} is not in this chunk "
                    f"({chunk_start_0 + 1}–{chunk_start_0 + chunk_len}); "
                    "use numbers as listed beside each line."
                )
            out.add(j)
    if not out:
        raise ValueError("no valid rule numbers parsed; use Enter for full regen.")
    return frozenset(out)


def parse_operator_notes_by_local_index(
    text: str,
    *,
    chunk_start_0: int,
    chunk_len: int,
) -> dict[int, str]:
    """
    Lines like ``12: fix modality`` map global rule number (1-based ordinal) to notes.
    Non-matching lines are ignored.
    """
    notes: dict[int, str] = {}
    for line in (text or "").splitlines():
        m = NOTE_LINE_RE.match(line)
        if not m:
            continue
        G = int(m.group(1))
        note = m.group(2).strip()
        if not note:
            continue
        j = G - chunk_start_0 - 1
        if 0 <= j < chunk_len:
            notes[j] = note
    return notes


def merge_pinned_chunk_lines(
    model_lines: list[str],
    *,
    baseline: list[str],
    revise_local: frozenset[int],
) -> list[str]:
    """Force non-revised slots to match ``baseline`` (same length)."""
    if len(model_lines) != len(baseline):
        raise ValueError("model_lines and baseline length mismatch")
    return [model_lines[i] if i in revise_local else baseline[i] for i in range(len(baseline))]


def run_wfm_chunk_scope_rewrite(
    chunk_rules: list[str],
    *,
    rule_index_start: int,
    rule_index_end_exclusive: int,
    file_label: str,
    coverage_report: ChunkCoverageReport,
    handoff_path: Path | None = None,
    llm: Callable[..., str] = pivot_llm_complete,
    working_baseline: list[str] | None = None,
    revise_local_indices: frozenset[int] | None = None,
    operator_notes_by_local_index: dict[int, str] | None = None,
) -> list[str]:
    """
    Return ``rewritten_rules`` with the same length as ``chunk_rules``.

    When ``revise_local_indices`` is non-empty, only those local positions may change relative to
    ``working_baseline`` (defaults to ``chunk_rules``); other positions are overwritten from the
    baseline after the LLM call. When ``revise_local_indices`` is ``None`` or empty frozenset,
    full-chunk revision, no pinning (empty frozenset is treated as full regen for safety).
    """
    n = len(chunk_rules)
    if n != rule_index_end_exclusive - rule_index_start:
        raise ValueError("chunk_rules length does not match index span")
    baseline = list(working_baseline) if working_baseline is not None else list(chunk_rules)
    if len(baseline) != n:
        raise ValueError("working_baseline length must match chunk_rules")

    subset = revise_local_indices is not None and len(revise_local_indices) > 0
    if subset:
        assert revise_local_indices is not None
        mode = "subset"
        idx_list = ", ".join(str(i) for i in sorted(revise_local_indices))
        notes = operator_notes_by_local_index or {}
        if notes:
            notes_lines = [
                f"- local_index={loc} global_rule_number={rule_index_start + loc + 1}: {txt}"
                for loc, txt in sorted(notes.items())
            ]
            notes_block = "\n".join(notes_lines)
        else:
            notes_block = "(none)"
    else:
        mode = "full"
        idx_list = "(all positions may change)"
        notes_block = "(not used in full mode)"

    tmpl = _prompt_template().replace(
        "<<<V1_ENCODABILITY>>>", read_v1_policy_encodability_contract()
    )
    summary = _coverage_summary(coverage_report)
    ho_sum = handoff_line_summary(handoff_path, max_rows=30) if handoff_path else "(no handoff path)"
    source_json = json.dumps(chunk_rules, ensure_ascii=False, indent=2)
    working_json = json.dumps(baseline, ensure_ascii=False, indent=2)
    prompt = (
        tmpl.replace("<<<FILE_LABEL>>>", file_label)
        .replace("<<<CHUNK_INDEX_RANGE>>>", f"{rule_index_start}..{rule_index_end_exclusive - 1} inclusive")
        .replace("<<<CHUNK_RULE_COUNT>>>", str(n))
        .replace("<<<CHUNK_RULES_JSON_ARRAY>>>", source_json)
        .replace("<<<WORKING_BASELINE_JSON_ARRAY>>>", working_json)
        .replace("<<<REVISION_MODE>>>", mode)
        .replace("<<<REVISE_LOCAL_INDICES_LIST>>>", idx_list)
        .replace("<<<OPERATOR_NOTES_BLOCK>>>", notes_block)
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

    if subset and revise_local_indices is not None:
        cleaned = merge_pinned_chunk_lines(
            cleaned,
            baseline=baseline,
            revise_local=revise_local_indices,
        )
    return cleaned


__all__ = [
    "handoff_line_summary",
    "merge_pinned_chunk_lines",
    "parse_operator_notes_by_local_index",
    "parse_rule_numbers_to_local_indices",
    "run_wfm_chunk_scope_rewrite",
]
