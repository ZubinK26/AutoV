"""WFM-only chunk loop (SMT profile, same handoffs as ``nl_chunk_smt_policy_pipeline`` without SMT)."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from nagv.paths import REPO_ROOT

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wfm_orchestration.handoff_artifacts import handoff_write_path
from wfm_orchestration.nl_chunk_policy_pipeline import format_chunk_for_wfm, parse_nl_rules
from wfm_orchestration.nl_chunk_smt_policy_pipeline import load_or_init_progress, save_progress
from wfm_orchestration.run_metadata import new_bundle_id


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# Agent 3 verdicts that may be fed to NagV formalizer (aligned with WFM / SMT forward policy).
_AGENT3_FORWARD = frozenset({"PASS", "REWRITE"})


def _lines_from_handoff_json(data: dict[str, Any]) -> list[Any]:
    """Registry handoffs use top-level ``lines``; some bundle artifacts nest under ``wfm_payload``."""
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
class NagvWfmNlAggregate:
    """Result of scanning WFM handoffs for NagV formalizer input."""

    ok: bool
    nl: str
    outcome: str  # empty if ok; else e.g. rejected_wfm_agent3
    message: str
    blocking_lines: list[dict[str, Any]] = field(default_factory=list)
    forward_line_count: int = 0


def aggregate_wfm_nl_for_nagv(
    *,
    repo_root: Path,
    work_dir: Path,
    print_fn: Callable[..., None] = print,
) -> NagvWfmNlAggregate:
    """
    Build concatenated NL for the formalizer (and critic/repair) from WFM handoffs.

    Each eligible line contributes **only** ``statement_nl`` (no line index or Agent3
    verdict tags — those stay in handoffs / ``wfm_nl_aggregate.json`` for debugging).

    Includes **PASS** and **REWRITE** lines. Any other Agent3 verdict (e.g. ``OUT_OF_SCOPE``),
    missing verdict, or empty ``statement_nl`` on a forward line **blocks** NagV — the
    pipeline must not run formalizer/Nagini until WFM is corrected.
    """
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

    report: dict[str, Any] = {
        "schema_version": "nagv_wfm_nl_aggregate_v1",
        "ok": len(blocking) == 0 and len(parts) > 0,
        "forward_line_count": len(parts),
        "blocking_line_count": len(blocking),
        "blocking_lines": blocking,
    }
    report_path = work_dir / "wfm_nl_aggregate.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if blocking:
        return NagvWfmNlAggregate(
            ok=False,
            nl="",
            outcome="rejected_wfm_agent3",
            message=(
                "WFM Agent3: one or more lines are not eligible for NagV "
                f"({len(blocking)} blocking; only PASS and REWRITE may proceed). "
                "See wfm_nl_aggregate.json."
            ),
            blocking_lines=blocking,
            forward_line_count=len(parts),
        )
    if not parts:
        return NagvWfmNlAggregate(
            ok=False,
            nl="",
            outcome="rejected_no_wfm_lines",
            message="No PASS/REWRITE lines found in WFM handoffs (or no handoffs readable).",
            blocking_lines=[],
            forward_line_count=0,
        )
    return NagvWfmNlAggregate(
        ok=True,
        nl="\n\n".join(parts),
        outcome="",
        message="",
        blocking_lines=[],
        forward_line_count=len(parts),
    )


def run_wfm_until_complete(
    *,
    repo_root: Path,
    nl_file: Path,
    work_dir: Path,
    rules_per_chunk: int,
    reset_progress: bool,
    print_fn: Callable[..., None] = print,
) -> int:
    """
    Run WFM (``wfm_profile=smt``) for each chunk until all rules are processed.
    Reuses ``nl_chunk_progress.json`` layout without ``pending_smt`` / SMT.
    """
    nl_file = nl_file.resolve()
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    if not nl_file.is_file():
        print_fn(f"error: NL file not found: {nl_file}", file=sys.stderr)
        return 2

    nl_hash = _sha256_file(nl_file)
    body = nl_file.read_text(encoding="utf-8")
    all_rules = parse_nl_rules(body)
    total = len(all_rules)
    if total == 0:
        print_fn("error: no rules after parsing NL.", file=sys.stderr)
        return 2

    progress_path = work_dir / "nl_chunk_progress.json"
    try:
        prog = load_or_init_progress(
            progress_path,
            nl_path=nl_file,
            nl_hash=nl_hash,
            rules_per_chunk=rules_per_chunk,
            work_dir=work_dir,
            force_reset=reset_progress,
        )
    except ValueError as e:
        print_fn(f"error: {e}", file=sys.stderr)
        return 2

    wfm_dir = work_dir / "wfm_handoffs"
    wfm_dir.mkdir(parents=True, exist_ok=True)

    from wfm_orchestration.e2e_context import create_e2e_context
    from wfm_orchestration.orchestrator import run_wfm_registry_e2e

    while prog.next_rule_index < total:
        start = prog.next_rule_index
        end = min(start + rules_per_chunk, total)
        chunk_rules = all_rules[start:end]
        chunk_seq = len(prog.chunk_records)
        bundle_id = new_bundle_id(prefix="nagvwfm")
        chunk_text = format_chunk_for_wfm(chunk_rules, start_index=start, file_label=nl_file.name)
        handoff_path = handoff_write_path(repo_root, bundle_id, handoff_dir=wfm_dir)

        print_fn(f"\n--- NagV WFM chunk: rules {start + 1}–{end} of {total}  bundle_id={bundle_id} ---\n")

        try:
            ctx = create_e2e_context(mock_resolve=True)
        except RuntimeError as e:
            print_fn(f"error: {e}", file=sys.stderr)
            return 2

        dev = run_wfm_registry_e2e(
            initial_user_text=chunk_text,
            client=ctx.client,
            model=ctx.model,
            temperature=ctx.temperature,
            max_output_tokens=ctx.max_output_tokens,
            thinking_level=ctx.thinking_level,
            registry_session=ctx.registry_session,
            llm_complete=ctx.llm_complete,
            bundle_id=bundle_id,
            bundle_id_prefix="nagvwfm",
            handoff_json=handoff_path,
            repo_root=repo_root,
            handoff_dir=wfm_dir,
            persist_handoff=True,
            skip_registry=True,
            auto_accept=True,
            auto_artifacts=False,
            example_id=f"nagv_{nl_file.stem}",
            wfm_profile="smt",
            global_rule_index_start=start,
            print_fn=print_fn,
        )

        if dev is None:
            print_fn("WFM failed (no handoff).", file=sys.stderr)
            return 1
        if not handoff_path.is_file():
            print_fn(f"error: missing handoff at {handoff_path}", file=sys.stderr)
            return 1

        try:
            hrel = str(handoff_path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            hrel = str(handoff_path.resolve())

        prog.chunk_records.append(
            {
                "chunk_seq": chunk_seq,
                "rule_index_start": start,
                "rule_index_end": end,
                "bundle_id": bundle_id,
                "handoff_relposix": hrel,
                "nagv_wfm_only": True,
            }
        )
        prog.next_rule_index = end
        prog.pending_smt = None
        save_progress(progress_path, prog)
        print_fn(f"OK: WFM chunk committed; next_rule_index={prog.next_rule_index}/{total}\n")

    print_fn(f"[NagV WFM] Finished all {total} rule(s).")
    return 0
