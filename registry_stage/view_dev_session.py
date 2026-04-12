"""
G8 — read-only **human-readable** views from a ``DevSessionSnapshot`` JSON export.

Writes Markdown under subfolders per pipeline stage (**search → extract → resolve → populate**).
Does **not** read or modify registry sources, bundles on disk, or the original export file.

Usage::

  python -m registry_stage.view_dev_session --input dev_session.json --out ./viewer_out
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _safe_name(line_index: int) -> str:
    return f"line_{line_index:02d}.md"


def _fence_json(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def _hits_table(rows: list[dict[str, Any]], *, title: str) -> str:
    if not rows:
        return f"### {title}\n\n*(none)*\n"
    lines = [f"### {title}", "", "| entry_id | score |", "|----------|-------|"]
    for r in rows:
        eid = str(r.get("entry_id", ""))
        sc = r.get("score", "")
        lines.append(f"| `{eid}` | {sc} |")
    lines.append("")
    return "\n".join(lines)


def render_search_markdown(trace: dict[str, Any]) -> str:
    bid = trace.get("bundle_id", "")
    li = trace.get("line_index", 0)
    stmt = trace.get("statement_nl", "")
    out = [
        f"# Search — bundle `{bid}` — line {li}",
        "",
        "## Statement (handoff line)",
        "",
        stmt.strip() or "*(empty)*",
        "",
        f"- **Agent 3 verdict:** `{trace.get('agent3_verdict', '')}`",
        f"- **Semantic backend:** `{trace.get('semantic_backend_label', '')}`",
        f"- **Authoritative min score:** `{trace.get('authoritative_min_score')}`",
        f"- **Single-concat query truncated:** `{trace.get('single_concat_query_truncated')}`",
        "",
    ]
    if trace.get("skipped_reason"):
        out.extend(["## Skipped", "", str(trace["skipped_reason"]), ""])
        return "\n".join(out)

    out.append("## Search queries used")
    out.append("")
    sq = trace.get("search_queries_used") or []
    if sq:
        for q in sq:
            out.append(f"- {q}")
    else:
        out.append("*(none)*")
    out.append("")
    out.append("## Expansion phrases")
    out.append("")
    ep = trace.get("expansion_phrases") or []
    if ep:
        for p in ep:
            out.append(f"- {p}")
    else:
        out.append("*(none)*")
    out.append("")
    out.append(_hits_table(trace.get("hits") or [], title="All hits"))
    out.append(_hits_table(trace.get("authoritative_hits") or [], title="Authoritative hits"))
    return "\n".join(out)


def render_extract_markdown(trace: dict[str, Any]) -> str:
    bid = trace.get("bundle_id", "")
    li = trace.get("line_index", 0)
    out = [
        f"# Extract (gaps) — bundle `{bid}` — line {li}",
        "",
    ]
    if trace.get("skipped_reason"):
        out.extend(["## Skipped", "", str(trace["skipped_reason"]), ""])
        return "\n".join(out)

    out.append("## Gap spans (NL fragments)")
    out.append("")
    gs = trace.get("gap_spans") or []
    if gs:
        for s in gs:
            out.append(f"- {s}")
    else:
        out.append("*(none)*")
    out.append("")
    out.append("## Structured gaps")
    out.append("")
    sg = trace.get("structured_gaps") or []
    if sg:
        out.append(_fence_json(sg))
    else:
        out.append("*(none)*")
    out.append("")
    out.append("## Raw structured gaps (pre-filter)")
    out.append("")
    raw = trace.get("raw_structured_gaps") or []
    if raw:
        out.append(_fence_json(raw))
    else:
        out.append("*(none)*")
    return "\n".join(out)


def render_resolve_markdown(trace: dict[str, Any]) -> str:
    bid = trace.get("bundle_id", "")
    li = trace.get("line_index", 0)
    out = [
        f"# Resolve — bundle `{bid}` — line {li}",
        "",
    ]
    if trace.get("skipped_reason"):
        out.extend(["## Skipped", "", str(trace["skipped_reason"]), ""])
        return "\n".join(out)

    out.extend(
        [
            "## Outcomes",
            "",
            f"- **resolve_mode:** `{trace.get('resolve_mode')}`",
            f"- **validation_outcome:** `{trace.get('validation_outcome')}`",
            f"- **attempts_used:** `{trace.get('attempts_used')}`",
            "",
            "### Pre-resolved NL",
            "",
            (trace.get("pre_resolved_nl") or "*(none)*").strip(),
            "",
            "### Registry resolution candidate NL",
            "",
            (trace.get("registry_resolution_candidate_nl") or "*(none)*").strip(),
            "",
            "### Registry resolved NL",
            "",
            (trace.get("registry_resolved_nl") or "*(none)*").strip(),
            "",
            "### LLM rationale (short)",
            "",
            (trace.get("llm_rationale_short") or "*(none)*").strip(),
            "",
        ]
    )
    fr = trace.get("failure_reasons") or []
    out.append("### Failure reasons")
    out.append("")
    if fr:
        for r in fr:
            out.append(f"- {r}")
    else:
        out.append("*(none)*")
    out.append("")
    raw_r = trace.get("raw_resolver_json") or []
    out.append("## Raw resolver JSON (per attempt)")
    out.append("")
    if raw_r:
        out.append(_fence_json(raw_r))
    else:
        out.append("*(none)*")
    return "\n".join(out)


def render_populate_markdown(trace: dict[str, Any]) -> str:
    bid = trace.get("bundle_id", "")
    li = trace.get("line_index", 0)
    out = [
        f"# Populate — bundle `{bid}` — line {li}",
        "",
    ]
    if trace.get("skipped_reason"):
        out.extend(["## Skipped", "", str(trace["skipped_reason"]), ""])
        return "\n".join(out)

    ids = trace.get("new_entry_ids") or []
    out.append("## New provisional entry IDs")
    out.append("")
    if ids:
        for i in ids:
            out.append(f"- `{i}`")
    else:
        out.append("*(none)*")
    out.append("")
    return "\n".join(out)


def render_handoff_overview(snapshot: dict[str, Any]) -> str:
    h = snapshot.get("handoff")
    if not h:
        return "# Handoff overview\n\n*(no handoff block in export)*\n"
    lines = [
        "# Handoff overview",
        "",
        f"- **bundle_id:** `{h.get('bundle_id', '')}`",
        f"- **orchestration_run_id:** `{h.get('orchestration_run_id', '')}`",
        f"- **provider_model:** `{h.get('provider_model', '')}`",
        "",
        "## User original input",
        "",
        (h.get("user_original_input") or "").strip() or "*(empty)*",
        "",
        "## Lines",
        "",
        "| idx | verdict | statement (preview) |",
        "|-----|---------|---------------------|",
    ]
    for ln in h.get("lines") or []:
        idx = ln.get("line_index", "")
        ver = ln.get("agent3_verdict", "")
        stmt = (ln.get("statement_nl") or "").replace("\n", " ")
        if len(stmt) > 120:
            stmt = stmt[:117] + "..."
        stmt = re.sub(r"\|", "\\|", stmt)
        lines.append(f"| {idx} | `{ver}` | {stmt} |")
    lines.append("")
    return "\n".join(lines)


def render_registry_summary(snapshot: dict[str, Any]) -> str:
    reg = snapshot.get("registry") or {}
    entries = reg.get("entries") or []
    lines = [
        "# Registry snapshot (export)",
        "",
        f"- **schema_version:** `{reg.get('schema_version', '')}`",
        f"- **entry count:** {len(entries)}",
        "",
        "## Entries",
        "",
        "| id | kind | name | status |",
        "|----|------|------|--------|",
    ]
    for e in entries:
        eid = str(e.get("id", ""))
        kind = str(e.get("kind", ""))
        name = str(e.get("name", "")).replace("|", "\\|")
        st = str(e.get("status", ""))
        lines.append(f"| `{eid}` | `{kind}` | {name} | `{st}` |")
    lines.append("")
    return "\n".join(lines)


def render_index(snapshot: dict[str, Any], *, bundle_id: str, n_lines: int) -> str:
    rows = [
        "# Dev session viewer (read-only)",
        "",
        f"- **bundle_id:** `{bundle_id}`",
        f"- **export schema_version:** `{snapshot.get('schema_version', '')}`",
        f"- **dev_export:** `{snapshot.get('dev_export')}`",
        "",
        "## Contents",
        "",
        "- [`handoff_overview.md`](handoff_overview.md) — WFM handoff lines (structured)",
        "- [`registry_summary.md`](registry_summary.md) — registry state in this export",
        "",
        "## Per-line traces (registry pipeline)",
        "",
        "Stages match the demo narrative: **search → extract → resolve → populate**.",
        "",
        "| line | search | extract | resolve | populate |",
        "|------|--------|---------|---------|----------|",
    ]
    if n_lines == 0:
        rows.append("| — | *(no `line_traces` in export)* | | | |")
    else:
        line_indices = [int(t.get("line_index", i)) for i, t in enumerate(snapshot.get("line_traces") or [])]
        for li in line_indices:
            name = _safe_name(li)
            rows.append(
                f"| {li} | [view](01_search/{name}) | [view](02_extract/{name}) | "
                f"[view](03_resolve/{name}) | [view](04_populate/{name}) |"
            )
    rows.append("")
    rows.append("---")
    rows.append("")
    rows.append("*Generated by `python -m registry_stage.view_dev_session` (G8).*")
    rows.append("")
    return "\n".join(rows)


def write_dev_session_views(snapshot: dict[str, Any], out_dir: Path) -> None:
    """
    Write Markdown trees under ``out_dir``. Creates ``out_dir`` and subfolders.
    **Read-only** with respect to project sources — only writes under ``out_dir``.
    """
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle_id = str(snapshot.get("bundle_id") or "unknown")

    for sub in ("01_search", "02_extract", "03_resolve", "04_populate"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    for trace in snapshot.get("line_traces") or []:
        li = int(trace.get("line_index", 0))
        name = _safe_name(li)
        (out_dir / "01_search" / name).write_text(render_search_markdown(trace), encoding="utf-8")
        (out_dir / "02_extract" / name).write_text(render_extract_markdown(trace), encoding="utf-8")
        (out_dir / "03_resolve" / name).write_text(render_resolve_markdown(trace), encoding="utf-8")
        (out_dir / "04_populate" / name).write_text(render_populate_markdown(trace), encoding="utf-8")

    (out_dir / "handoff_overview.md").write_text(render_handoff_overview(snapshot), encoding="utf-8")
    (out_dir / "registry_summary.md").write_text(render_registry_summary(snapshot), encoding="utf-8")
    lt = snapshot.get("line_traces") or []
    (out_dir / "index.md").write_text(
        render_index(snapshot, bundle_id=bundle_id, n_lines=len(lt)),
        encoding="utf-8",
    )


def _load_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("snapshot root must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="G8 — render read-only Markdown viewers from a DevSessionSnapshot JSON export."
    )
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to dev session JSON (from --export / export_session).",
    )
    p.add_argument(
        "--out",
        "-o",
        type=Path,
        required=True,
        help="Output directory for Markdown tree (created if missing).",
    )
    args = p.parse_args(argv)

    if not args.input.is_file():
        print(f"error: file not found: {args.input}", file=sys.stderr)
        return 2

    try:
        snap = _load_snapshot(args.input)
        write_dev_session_views(snap, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(f"Wrote read-only viewers under: {args.out.resolve()}")
    print(f"Open: {args.out.resolve() / 'index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
