"""Drop policy rules during Phase 0 WFM (shared by confirm-omit and coverage-repair [d])."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_effective_source_nl(work_dir: Path, all_rules: list[str]) -> Path:
    """Persist the in-memory policy slice after drops (used by post–Phase 0 count gate)."""
    work_dir = work_dir.resolve()
    path = work_dir / "pivot_wfm_effective_source.nl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(all_rules)
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path


def append_drop_record(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "pivot_wfm_dropped_rules.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as lf:
        lf.write(json.dumps(record, ensure_ascii=False) + "\n")


def drop_rules_at_global_indices(
    all_rules: list[str],
    global_indices: list[int],
    *,
    work_dir: Path,
    reason: str,
    bundle_id: str | None = None,
    chunk_rule_index_start: int | None = None,
    chunk_rule_index_end: int | None = None,
) -> list[int]:
    """
    Remove rules at global 0-based indices (highest index first).

    Returns indices actually dropped (sorted ascending).
    """
    work_dir = work_dir.resolve()
    to_drop = sorted({int(i) for i in global_indices}, reverse=True)
    dropped_asc: list[int] = []
    for di in to_drop:
        if di < 0 or di >= len(all_rules):
            raise ValueError(f"drop index {di} outside policy (len={len(all_rules)})")
        line = all_rules.pop(di)
        dropped_asc.append(di)
        rec: dict[str, Any] = {
            "rule_index_dropped": di,
            "line": line,
            "reason": reason,
        }
        if bundle_id:
            rec["chunk_bundle_id"] = bundle_id
        if chunk_rule_index_start is not None:
            rec["chunk_rule_index_start"] = chunk_rule_index_start
        if chunk_rule_index_end is not None:
            rec["chunk_rule_index_end"] = chunk_rule_index_end
        append_drop_record(work_dir, rec)
    dropped_asc.sort()
    if dropped_asc:
        write_effective_source_nl(work_dir, all_rules)
    return dropped_asc


__all__ = [
    "append_drop_record",
    "drop_rules_at_global_indices",
    "write_effective_source_nl",
]
