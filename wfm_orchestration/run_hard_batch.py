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

By default, **only** example ids that have a reference ``.lp`` in ``wfm_ground_truth_asp_map.json``
(on disk) are scheduled — the rest are skipped for API (FOLIO/P-FOLIO/stress text alone is not
scorable for ASP). Use ``--curated-without-asp-reference`` to run the full list anyway.
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
    ap.add_argument(
        "--curated-without-asp-reference",
        action="store_true",
        help=(
            "Ignore wfm_ground_truth_asp_map.json and run all batch ids (WFM on narrative-only problems "
            "with no in-repo reference LP; not for automatic ASP scoring)."
        ),
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

    from wfm_orchestration.ground_truth_asp import (
        curated_id_has_ground_truth_lp,
        load_ground_truth_asp_map,
        truth_assessment_curated_wfm,
    )

    gmap = load_ground_truth_asp_map(_REPO)
    if args.curated_without_asp_reference:
        scheduled_ids: list[str] = list(ids)
        not_assessable: list[str] = []
    else:
        scheduled_ids = [eid for eid in ids if curated_id_has_ground_truth_lp(_REPO, eid, gmap)]
        not_assessable = [eid for eid in ids if eid not in set(scheduled_ids)]

    if args.dry_run:
        print(f"batch_json={batch_path}")
        print(f"delay_sec={delay}")
        print(f"skip_existing={skip_existing}")
        if not args.curated_without_asp_reference:
            print("ground_truth_gate=manifest (wfm_ground_truth_asp_map.json)")
        else:
            print("ground_truth_gate=off (--curated-without-asp-reference)")
        if not args.curated_without_asp_reference and not_assessable:
            print("Not schedulable (no reference .lp in manifest):")
            for ex_id in not_assessable:
                t = truth_assessment_curated_wfm(ex_id, repo_root=_REPO, m=gmap)
                print(f"  {ex_id}  assessable_against_stored_reference_asp={t.get('assessable_against_stored_reference_asp')!r}")
        if not args.curated_without_asp_reference and not scheduled_ids:
            print("Schedulable with stored reference LP: (none) — add paths to the manifest to run WFM for ASP scoring.")
        else:
            print("Schedulable with stored reference LP:" if not args.curated_without_asp_reference else "All batch ids (no manifest gate):")
            for ex_id in scheduled_ids:
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
    for ex_id in scheduled_ids:
        if skip_existing and list_existing_handoffs_for_batch_example(_REPO, ex_id):
            skipped.append(ex_id)
        else:
            to_run.append(ex_id)

    if skipped:
        print(
            f"[batch] Skipping {len(skipped)} example(s) with existing handoff JSON: {', '.join(skipped)}\n",
            flush=True,
        )
    if not scheduled_ids and not args.curated_without_asp_reference:
        print(
            "[batch] No example ids have a reference .lp in wfm_ground_truth_asp_map.json. "
            "Add curated_id_to_reference_lp entries (paths must exist), or pass "
            "--curated-without-asp-reference to run the narrative batch anyway.\n"
        )
        return 0
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
            f"\n========== Batch {j + 1}/{len(to_run)} (manifest-eligible {len(scheduled_ids)} of {len(ids)} in file)  "
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
