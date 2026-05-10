"""Concatenate PASS/REWRITE ``statement_nl`` from pivot WFM handoffs (same shape as NagV / SMT)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


_AGENT3_FORWARD = frozenset({"PASS", "REWRITE"})


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


@dataclass
class PivotWfmAggregate:
    ok: bool
    nl: str
    outcome: str
    message: str
    blocking_lines: list[dict[str, Any]] = field(default_factory=list)
    forward_line_count: int = 0


def aggregate_pivot_wfm_nl(
    *,
    repo_root: Path,
    work_dir: Path,
    print_fn: Callable[..., None] = print,
) -> PivotWfmAggregate:
    work_dir = work_dir.resolve()
    progress_path = work_dir / "nl_chunk_progress.json"
    parts: list[str] = []
    blocking: list[dict[str, Any]] = []
    if not progress_path.is_file():
        print_fn(f"warning: no {progress_path}; scanning wfm_handoffs/*.json", file=sys.stderr)
        ho_dir = work_dir / "wfm_handoffs"
        files = sorted(ho_dir.glob("*.json")) if ho_dir.is_dir() else []
    else:
        prog_raw = json.loads(progress_path.read_text(encoding="utf-8"))
        files = []
        for rec in sorted(prog_raw.get("chunk_records") or [], key=lambda r: r.get("chunk_seq", 0)):
            rel = rec.get("handoff_relposix")
            if not rel:
                continue
            p = repo_root / rel
            if p.is_file():
                files.append(p)

    seen: set[str] = set()
    for hp in files:
        key = str(hp.resolve())
        if key in seen:
            continue
        seen.add(key)
        try:
            data = json.loads(hp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print_fn(f"warning: skip handoff {hp}: {e}", file=sys.stderr)
            continue
        bundle_id = str(
            data.get("bundle_id")
            or (isinstance(data.get("wfm_payload"), dict) and data["wfm_payload"].get("bundle_id"))
            or hp.stem
        )
        for row in sorted(_lines_from_handoff_json(data), key=lambda x: int(x.get("line_index", 0))):
            v = str(row.get("agent3_verdict") or "").strip().upper()
            nl = str(row.get("statement_nl") or "").strip()
            li = row.get("line_index")
            if v in _AGENT3_FORWARD:
                if not nl:
                    blocking.append(
                        {
                            "bundle_id": bundle_id,
                            "handoff": str(hp),
                            "line_index": li,
                            "agent3_verdict": v,
                            "reason": "empty_statement_nl",
                        }
                    )
                    continue
                parts.append(nl)
            else:
                blocking.append(
                    {
                        "bundle_id": bundle_id,
                        "handoff": str(hp),
                        "line_index": li,
                        "agent3_verdict": v or "(missing)",
                        "statement_nl_preview": (nl[:240] + "...") if len(nl) > 240 else nl,
                    }
                )

    report_path = work_dir / "pivot_wfm_nl_aggregate.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "schema_version": "pivot_wfm_nl_aggregate_v1",
                "ok": len(blocking) == 0 and len(parts) > 0,
                "forward_line_count": len(parts),
                "blocking_line_count": len(blocking),
                "blocking_lines": blocking,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    if blocking:
        return PivotWfmAggregate(
            ok=False,
            nl="",
            outcome="rejected_wfm_agent3",
            message=(
                f"WFM blocked ({len(blocking)} line(s)); see pivot_wfm_nl_aggregate.json — "
                "fix NL and re-run Phase 0."
            ),
            blocking_lines=blocking,
            forward_line_count=len(parts),
        )
    if not parts:
        return PivotWfmAggregate(
            ok=False,
            nl="",
            outcome="rejected_no_wfm_lines",
            message="No PASS/REWRITE lines in pivot WFM handoffs.",
            blocking_lines=[],
            forward_line_count=0,
        )
    return PivotWfmAggregate(
        ok=True,
        nl="\n\n".join(parts),
        outcome="",
        message="",
        blocking_lines=[],
        forward_line_count=len(parts),
    )
