"""
Run WFM on a fixed list of hard curated examples, pacing requests to reduce Gemini rate-limit risk.

Usage (from repo root)::

  set WFM_BATCH_DELAY_SEC=90
  python -m wfm_orchestration.run_hard_batch

Environment:

- ``GEMINI_API_KEY`` — required.
- ``WFM_BATCH_DELAY_SEC`` — seconds between examples (default: 90).
- ``WFM_BATCH_JSON`` — override path to batch JSON (default: ``wfm_hard_batch_curated.json`` next to this file).

Resume: by default, skips any example that already has ``bundles/wfm_artifacts/hard_<id>_*.json``.
Use ``--force-rerun`` to ignore that and run all 12 again (new bundle ids; does not delete old files).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_BATCH = Path(__file__).resolve().parent / "wfm_hard_batch_curated.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="WFM hard batch → handoff JSON (skip registry) with pacing.")
    ap.add_argument(
        "--batch-json",
        type=Path,
        default=None,
        help=f"Batch descriptor JSON (default: {_DEFAULT_BATCH.name})",
    )
    ap.add_argument(
        "--delay-sec",
        type=float,
        default=None,
        help="Seconds to sleep between examples (default: env WFM_BATCH_DELAY_SEC or 90).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print example ids and exit (no Gemini).",
    )
    ap.add_argument(
        "--force-rerun",
        action="store_true",
        help="Run every example even if a handoff file already exists for that id.",
    )
    args = ap.parse_args(argv)

    batch_path = args.batch_json or Path(os.environ.get("WFM_BATCH_JSON", str(_DEFAULT_BATCH)))
    if not batch_path.is_file():
        print(f"error: batch file not found: {batch_path}", file=sys.stderr)
        return 2

    raw = json.loads(batch_path.read_text(encoding="utf-8"))
    ids: list[str] = list(raw.get("example_ids") or [])
    if not ids:
        print("error: example_ids empty in batch JSON", file=sys.stderr)
        return 2

    delay = args.delay_sec
    if delay is None:
        delay = float(os.environ.get("WFM_BATCH_DELAY_SEC", "90"))

    from wfm_orchestration.handoff_artifacts import (
        hard_batch_bundle_prefix,
        list_existing_handoffs_for_batch_example,
    )

    skip_existing = not args.force_rerun

    if args.dry_run:
        print(f"batch_json={batch_path}")
        print(f"delay_sec={delay}")
        print(f"skip_existing={skip_existing}")
        for ex_id in ids:
            existing = list_existing_handoffs_for_batch_example(_REPO, ex_id) if skip_existing else []
            if existing:
                print(f"  {ex_id}  [skip - handoff exists: {existing[-1].name}]")
            else:
                print(f"  {ex_id}  [run]")
        return 0

    from wfm_orchestration.demo_loader import get_curated_example_text, load_demo_pool_config
    from wfm_orchestration.e2e_context import create_e2e_context, load_dotenv_for_e2e
    from wfm_orchestration.orchestrator import run_wfm_registry_e2e

    load_dotenv_for_e2e()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("error: set GEMINI_API_KEY for WFM", file=sys.stderr)
        return 2
    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("error: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    cfg = load_demo_pool_config()
    ctx = create_e2e_context(mock_resolve=False)

    to_run: list[str] = []
    skipped: list[str] = []
    for ex_id in ids:
        if skip_existing and list_existing_handoffs_for_batch_example(_REPO, ex_id):
            skipped.append(ex_id)
        else:
            to_run.append(ex_id)

    if skipped:
        print(
            f"[batch] Skipping {len(skipped)} example(s) with existing handoff JSON: {', '.join(skipped)}\n",
            flush=True,
        )
    if not to_run:
        print("[batch] Nothing left to run (all examples already have handoff files). Use --force-rerun to redo.")
        return 0

    failures: list[tuple[str, str]] = []
    for j, ex_id in enumerate(to_run):
        if j > 0:
            print(f"\n[batch] Sleeping {delay}s before next example...\n", flush=True)
            time.sleep(delay)
        prefix = hard_batch_bundle_prefix(ex_id)
        try:
            text = get_curated_example_text(ex_id, cfg=cfg)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(
            f"\n========== Batch {j + 1}/{len(to_run)} (list {len(ids)})  "
            f"example_id={ex_id}  bundle_prefix={prefix} ==========\n"
        )
        out = run_wfm_registry_e2e(
            initial_user_text=text,
            client=ctx.client,
            model=ctx.model,
            temperature=ctx.temperature,
            max_output_tokens=ctx.max_output_tokens,
            thinking_level=ctx.thinking_level,
            registry_session=ctx.registry_session,
            llm_complete=ctx.llm_complete,
            bundle_id_prefix=prefix,
            provider_model=ctx.model,
            repo_root=_REPO,
            persist_handoff=True,
            example_id=ex_id,
            auto_accept=True,
            skip_registry=True,
            auto_artifacts=False,
        )
        if out is None:
            failures.append((ex_id, "WFM returned None (limit/abort/failure)"))
            print(f"[batch] FAILED: {ex_id}", file=sys.stderr)

    if failures:
        print("\n[batch] Completed with failures:", file=sys.stderr)
        for ex_id, msg in failures:
            print(f"  {ex_id}: {msg}", file=sys.stderr)
        return 1
    print("\n[batch] All scheduled examples in this run finished OK.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
