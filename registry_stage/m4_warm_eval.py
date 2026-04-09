"""
M4 warm-registry empirical harness (Phase 1) — **two-bundle** run → JSONL.

**Why two bundles (not one):** validates the conditions you care about for real demos:
(1) **populate** after bundle A creates rows that **semantic search** can hit,
(2) bundle B lines use **different surface wording** so you see **retrieval + resolve**
    under realistic paraphrase, not only cold-start.

**Prerequisites:** repo-root ``.env`` with ``GEMINI_API_KEY`` (see ``registry_stage/llm/gemini_call.py``).
Heavy stack: ``faiss`` + ``sentence-transformers`` (default ``--index faiss``). Quick connectivity check:
``--index stub`` (Retrieval quality differs; prefer **faiss** for honest M4 conditions).

**Run (from repo root):**

 POSIX::

   python -m registry_stage.m4_warm_eval \\
       --out registry_stage/eval_runs/m4_warm_eval_$(date -u +%Y%m%d%H%M%S).jsonl

 PowerShell::

   python -m registry_stage.m4_warm_eval --out registry_stage/eval_runs/m4_warm_eval.jsonl

Optional: ``--after-seed-registry registry_stage/eval_runs/m4_after_seed.json`` to keep the
intermediate registry artifact (defaults next to ``--out`` with suffix ``_after_seed_registry.json``).

**Analyze:** open the JSONL: ``row_kind == \"result\"``. For **reuse** phase rows, check
``authoritative_hit_ids`` (non-empty ⇒ warm start worked) and ``resolve_success`` /
``registry_resolved_nl`` / ``cited_entry_ids`` for M4 behavior. Use this corpus before tuning
numeric guardrails or resolve prompts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from registry_stage.bundle_workflow import registry_session_to_registry_file, run_bundle_through_registry
from registry_stage.line_driver import LineDriverConfig
from registry_stage.llm.agents import PROMPTS_DIR
from registry_stage.llm.gemini_call import gemini_complete
from registry_stage.loaders import load_handoff_bundle, load_registry, save_registry
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head_short() -> str | None:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if root.returncode != 0:
            return None
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            cwd=root.stdout.strip(),
        )
        if rev.returncode != 0:
            return None
        return rev.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def _session(*, index: str) -> RegistrySession:
    if index == "stub":
        return RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    return RegistrySession(index_preference="faiss")


def _line_config() -> LineDriverConfig:
    return LineDriverConfig(
        enable_llm=True,
        query_mode="single_concat",
        masking_preset="conservative",
    )


def _cited_from_trace(trace: dict[str, Any]) -> list[str]:
    cited: list[str] = []
    for block in trace.get("raw_resolver_json") or []:
        if not isinstance(block, dict) or "_error" in block:
            continue
        raw = block.get("cited_entry_ids")
        if isinstance(raw, list):
            cited = [str(x) for x in raw]
    return cited


def _trace_to_row(
    *,
    warm_phase: str,
    trace: dict[str, Any],
    registry_entry_count_after: int,
) -> dict[str, Any]:
    auth = trace.get("authoritative_hits") or []
    auth_ids = [h.get("entry_id") for h in auth if isinstance(h, dict)] if auth else []
    vo = trace.get("validation_outcome")
    skipped = vo == "skipped" or trace.get("skipped_reason")
    resolve_success = (
        not skipped
        and vo == "passed"
        and trace.get("registry_resolved_nl") is not None
    )
    return {
        "row_kind": "result",
        "warm_phase": warm_phase,
        "bundle_id": trace.get("bundle_id"),
        "line_index": trace.get("line_index"),
        "statement_nl": trace.get("statement_nl"),
        "agent3_verdict": trace.get("agent3_verdict"),
        "skipped_reason": trace.get("skipped_reason"),
        "validation_outcome": vo,
        "resolve_success": resolve_success,
        "registry_resolved_nl": trace.get("registry_resolved_nl"),
        "failure_reasons": trace.get("failure_reasons"),
        "cited_entry_ids": _cited_from_trace(trace),
        "authoritative_hit_ids": auth_ids,
        "authoritative_min_score": trace.get("authoritative_min_score"),
        "semantic_backend_label": trace.get("semantic_backend_label"),
        "gap_spans": trace.get("gap_spans"),
        "new_entry_ids": trace.get("new_entry_ids"),
        "attempts_used": trace.get("attempts_used"),
        "registry_entry_count_after_line": registry_entry_count_after,
    }


def default_seed_path() -> Path:
    return Path(__file__).resolve().parent / "eval_fixtures" / "m4_warm_seed_bundle.json"


def default_reuse_path() -> Path:
    return Path(__file__).resolve().parent / "eval_fixtures" / "m4_warm_reuse_bundle.json"


def run_warm_eval(
    *,
    out_path: Path,
    seed_bundle_path: Path,
    reuse_bundle_path: Path,
    index_mode: str,
    after_seed_registry_path: Path | None,
    eval_label: str,
) -> None:
    def llm_complete(system: str, user: str) -> str:
        return gemini_complete(system_instruction=system, user_text=user)

    seed = load_handoff_bundle(seed_bundle_path)
    reuse = load_handoff_bundle(reuse_bundle_path)

    expand_md = PROMPTS_DIR / "registry_search_expand.md"
    gap_md = PROMPTS_DIR / "registry_gap_extract.md"
    resolve_md = PROMPTS_DIR / "registry_resolve_automated.md"

    header: dict[str, Any] = {
        "row_kind": "header",
        "eval_protocol_version": "m4_warm_eval_v1",
        "eval_label": eval_label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "gemini_model": os.environ.get("GEMINI_MODEL", ""),
        "index_mode": index_mode,
        "seed_bundle_path": str(seed_bundle_path.as_posix()),
        "reuse_bundle_path": str(reuse_bundle_path.as_posix()),
        "line_driver": {
            "query_mode": "single_concat",
            "masking_preset": "conservative",
            "enable_llm": True,
        },
        "prompt_sha256": {
            "registry_search_expand.md": _sha256_file(expand_md),
            "registry_gap_extract.md": _sha256_file(gap_md),
            "registry_resolve_automated.md": _sha256_file(resolve_md),
        },
        "git_commit_short": _git_head_short(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    inter_registry = after_seed_registry_path
    if inter_registry is None:
        inter_registry = out_path.with_name(out_path.stem + "_after_seed_registry.json")

    session = _session(index=index_mode)
    snap_seed = run_bundle_through_registry(
        seed,
        session,
        llm_complete=llm_complete,
        line_config=_line_config(),
    )
    save_registry(inter_registry, registry_session_to_registry_file(session))

    reg_mid = load_registry(inter_registry)
    if index_mode == "stub":
        session_reuse = RegistrySession.from_entries(
            reg_mid.entries,
            semantic_index=StubKeywordSemanticIndex(),
            index_preference="stub",
        )
    else:
        session_reuse = RegistrySession.from_entries(reg_mid.entries, index_preference="faiss")

    snap_reuse = run_bundle_through_registry(
        reuse,
        session_reuse,
        llm_complete=llm_complete,
        line_config=_line_config(),
    )

    header["after_seed_registry_path"] = str(inter_registry.as_posix())
    header["seed_line_count"] = len(snap_seed.line_traces)
    header["reuse_line_count"] = len(snap_reuse.line_traces)
    header["registry_entries_after_seed"] = len(snap_seed.registry.entries) if snap_seed.registry else 0
    header["registry_entries_after_reuse"] = len(snap_reuse.registry.entries) if snap_reuse.registry else 0

    with out_path.open("w", encoding="utf-8") as fp:
        fp.write(json.dumps(header, ensure_ascii=False) + "\n")
        cum_seed = 0
        for tr in snap_seed.line_traces:
            if isinstance(tr, dict):
                cum_seed += len(tr.get("new_entry_ids") or [])
                fp.write(
                    json.dumps(
                        _trace_to_row(warm_phase="seed", trace=tr, registry_entry_count_after=cum_seed),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        base_reuse = len(reg_mid.entries)
        cum_reuse = base_reuse
        for tr in snap_reuse.line_traces:
            if isinstance(tr, dict):
                cum_reuse += len(tr.get("new_entry_ids") or [])
                fp.write(
                    json.dumps(
                        _trace_to_row(warm_phase="reuse", trace=tr, registry_entry_count_after=cum_reuse),
                        ensure_ascii=False,
                    )
                    + "\n"
                )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="M4 warm-registry eval → JSONL (seed bundle then reuse bundle).")
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSONL path (header row + one result row per line)",
    )
    p.add_argument("--seed-bundle", type=Path, default=None, help="Default: eval_fixtures/m4_warm_seed_bundle.json")
    p.add_argument("--reuse-bundle", type=Path, default=None, help="Default: eval_fixtures/m4_warm_reuse_bundle.json")
    p.add_argument("--index", choices=("faiss", "stub"), default="faiss")
    p.add_argument(
        "--after-seed-registry",
        type=Path,
        default=None,
        help="Write registry after seed bundle here (default: next to --out with _after_seed_registry.json)",
    )
    p.add_argument("--label", type=str, default="m4_warm", help="eval_label in header")
    args = p.parse_args(argv)

    seed_p = args.seed_bundle or default_seed_path()
    reuse_p = args.reuse_bundle or default_reuse_path()
    if not seed_p.is_file():
        raise SystemExit(f"seed bundle not found: {seed_p}")
    if not reuse_p.is_file():
        raise SystemExit(f"reuse bundle not found: {reuse_p}")

    run_warm_eval(
        out_path=args.out,
        seed_bundle_path=seed_p,
        reuse_bundle_path=reuse_p,
        index_mode=args.index,
        after_seed_registry_path=args.after_seed_registry,
        eval_label=args.label,
    )
    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
