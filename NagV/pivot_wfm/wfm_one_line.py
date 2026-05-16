"""Run pivot WFM on a single NL rule line (scratch work_dir under parent)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable
from uuid import uuid4

from wfm_orchestration.nl_chunk_policy_pipeline import parse_nl_rules


def run_pivot_wfm_one_line(
    line: str,
    *,
    repo_root: Path,
    scratch_parent: Path,
    print_fn: Callable[..., None] = print,
) -> str:
    """Return Agent-3 ``statement_nl`` for one rule (PASS/REWRITE), WFM-normalized."""
    from pivot_wfm.aggregate import aggregate_pivot_wfm_nl
    from pivot_wfm.run_wfm_phase import run_pivot_wfm_until_complete

    line = line.strip()
    if not line:
        raise ValueError("run_pivot_wfm_one_line: empty line")

    scratch_parent = scratch_parent.resolve()
    scratch_parent.mkdir(parents=True, exist_ok=True)
    scratch = scratch_parent / f"wfm_rewrite_{uuid4().hex[:10]}"
    scratch.mkdir(parents=True, exist_ok=True)
    nl_path = scratch / "single_rule.nl"
    nl_path.write_text(line + "\n", encoding="utf-8")

    rc = run_pivot_wfm_until_complete(
        repo_root=repo_root.resolve(),
        nl_file=nl_path,
        work_dir=scratch,
        rules_per_chunk=1,
        reset_progress=True,
        print_fn=print_fn,
        auto_accept_wfm=True,
    )
    if rc != 0:
        raise RuntimeError(f"pivot WFM one-line failed (exit {rc}); scratch={scratch}")

    agg = aggregate_pivot_wfm_nl(repo_root=repo_root, work_dir=scratch, print_fn=print_fn)
    if not agg.ok:
        print_fn(f"[wfm_one_line] aggregate message: {agg.message}", file=sys.stderr)
        raise RuntimeError(f"pivot WFM one-line aggregate not ok: {agg.outcome or agg.message}")
    out_lines = parse_nl_rules(agg.nl)
    if not out_lines:
        raise RuntimeError("pivot WFM one-line produced no forward lines")
    return out_lines[0].strip()


__all__ = ["run_pivot_wfm_one_line"]
