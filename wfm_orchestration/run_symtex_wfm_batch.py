"""
Batch-run SymTex (demo option 1) through WFM with resume-safe state.

Only **paired** SymTex rows (NL + reference ASP in the ASPBench JSONL) are ever scheduled; there is
no separate pool of "no ground truth" examples to filter out. Completed JSONL includes a
``truth_assessment`` field marking runs as scorable against the stored reference program.

Successful handoffs append ``completed.jsonl``. Failures (e.g. Gemini 503) are not recorded,
so the next run skips completed ``task:source_id`` keys and shuffles the remaining pool.

Run from repo root::

  python -m wfm_orchestration.run_symtex_wfm_batch --limit 5
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from wfm_orchestration.asp_demo_sources import SymTexPairedExample, load_symtex_paired_index
from wfm_orchestration.ground_truth_asp import truth_assessment_symtex_paired
from wfm_orchestration.e2e_context import create_e2e_context, load_dotenv_for_e2e
from wfm_orchestration.handoff_artifacts import handoff_write_path
from wfm_orchestration.orchestrator import run_wfm_registry_e2e


def symtex_example_key(ex: SymTexPairedExample) -> str:
    return f"{ex.task}:{ex.source_id}"


def default_state_dir(repo_root: Path) -> Path:
    return repo_root / "exports" / "wfm_symtex_batch"


def completed_jsonl_path(state_dir: Path) -> Path:
    return state_dir / "completed.jsonl"


def load_completed_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("success") is True and isinstance(row.get("example_key"), str):
            keys.add(row["example_key"])
    return keys


def append_completed(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def pending_examples(
    index: list[SymTexPairedExample],
    completed: set[str],
) -> list[SymTexPairedExample]:
    return [ex for ex in index if symtex_example_key(ex) not in completed]


def run_symtex_batch(
    *,
    repo_root: Path,
    limit: int,
    state_dir: Path,
    rng: random.Random,
    skip_registry: bool,
    auto_artifacts: bool,
    dry_run: bool,
    run_wfm: Callable[..., Any] | None = None,
    delay_sec: float = 0.0,
) -> int:
    """
    Run up to ``limit`` SymTex examples not in ``completed.jsonl``.

    Returns 1 if SymTex index missing; 2 if GEMINI not configured; 0 otherwise.
    """
    state_dir = state_dir.resolve()
    cpath = completed_jsonl_path(state_dir)
    try:
        index = load_symtex_paired_index(repo_root)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    completed = load_completed_keys(cpath)
    pending = pending_examples(index, completed)
    if not pending:
        print(f"No pending SymTex examples (all {len(index)} keys in {cpath}).")
        return 0

    # Entire index is already paired with reference_asp; nothing is "no GT" in this batch.

    rng.shuffle(pending)
    to_run = pending[:limit]

    if dry_run:
        print(
            f"Truth scoring: all SymTex runs here are paired with reference ASP in the clone "
            f"(index={len(index)} examples; {len(pending)} pending vs completed state)."
        )
        print(f"Would run {len(to_run)} example(s) (limit={limit}, pending={len(pending)}):")
        for ex in to_run:
            print(
                f"  - {symtex_example_key(ex)}  manifest={ex.manifest_example_id}  "
                f"assessable_ref={bool(ex.reference_asp_program.strip())}"
            )
        return 0

    load_dotenv_for_e2e()
    try:
        ctx = create_e2e_context(mock_resolve=skip_registry)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    runner = run_wfm or run_wfm_registry_e2e
    successes = 0
    failures = 0

    for i, ex in enumerate(to_run, 1):
        if i > 1 and delay_sec > 0:
            time.sleep(delay_sec)
        key = symtex_example_key(ex)
        print(f"\n{'='*60}\n[{i}/{len(to_run)}] {key}\n{'='*60}\n")
        try:
            out = runner(
                initial_user_text=ex.nl_document,
                client=ctx.client,
                model=ctx.model,
                temperature=ctx.temperature,
                max_output_tokens=ctx.max_output_tokens,
                thinking_level=ctx.thinking_level,
                registry_session=ctx.registry_session,
                llm_complete=ctx.llm_complete,
                bundle_id_prefix="symtex_batch",
                repo_root=repo_root,
                persist_handoff=True,
                example_id=ex.manifest_example_id,
                auto_accept=True,
                skip_registry=skip_registry,
                provider_model=ctx.model,
                auto_artifacts=auto_artifacts,
            )
        except Exception as e:
            failures += 1
            print(f"[fail] API or runtime error: {e}", file=sys.stderr)
            traceback.print_exc()
            continue

        if out is None or getattr(out, "bundle", None) is None:
            failures += 1
            print("[fail] WFM returned no handoff (LIMIT_EXCEEDED, merge abort, etc.).", file=sys.stderr)
            continue

        bundle = out.bundle
        handoff_path = handoff_write_path(repo_root, bundle.bundle_id)
        record = {
            "success": True,
            "example_key": key,
            "task": ex.task,
            "source_id": ex.source_id,
            "manifest_example_id": ex.manifest_example_id,
            "bundle_id": bundle.bundle_id,
            "handoff_path": str(handoff_path.resolve()),
            "utc": datetime.now(timezone.utc).isoformat(),
            "truth_assessment": truth_assessment_symtex_paired(ex),
        }
        append_completed(cpath, record)
        successes += 1
        print(f"[ok] Recorded in {cpath.name}: {key} -> bundle {bundle.bundle_id}")

    print(f"\nDone: {successes} succeeded, {failures} failed this run. State: {cpath}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Batch WFM for ASPBench SymTex with resume via completed.jsonl.")
    p.add_argument("--limit", type=int, default=5, help="Max examples to attempt this run (default 5).")
    p.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Directory for completed.jsonl (default: exports/wfm_symtex_batch).",
    )
    p.add_argument("--seed", type=int, default=None, help="RNG seed for ordering pending examples.")
    p.add_argument(
        "--full-registry",
        action="store_true",
        help="Run registry stage after handoff (more Gemini calls; default is handoff-only).",
    )
    p.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip exports/e2e_demo_runs auto artifacts per orchestrator.",
    )
    p.add_argument("--dry-run", action="store_true", help="List examples that would run; no API.")
    p.add_argument(
        "--delay-sec",
        type=float,
        default=0.0,
        help="Delay between WFM runs (e.g. 5) to avoid rate limits.",
    )
    args = p.parse_args(argv)

    repo_root = _REPO
    state_dir = args.state_dir if args.state_dir is not None else default_state_dir(repo_root)
    rng = random.Random(args.seed)

    try:
        from google import genai  # noqa: F401
    except ImportError:
        if not args.dry_run:
            print("error: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
            return 2

    return run_symtex_batch(
        repo_root=repo_root,
        limit=max(1, args.limit),
        state_dir=state_dir,
        rng=rng,
        skip_registry=not args.full_registry,
        auto_artifacts=not args.no_artifacts,
        dry_run=args.dry_run,
        delay_sec=max(0.0, args.delay_sec),
    )


if __name__ == "__main__":
    raise SystemExit(main())
