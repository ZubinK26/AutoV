"""
Batch-run ``smt_pipeline`` on WFM handoff JSON files: one policy model per handoff, resume-friendly.

From repo root::

  python -m smt_pipeline.run_wfm_handoff_batch --delay-sec 30
  python -m smt_pipeline.run_wfm_handoff_batch --dry-run

Uses the same Gemini env contract as ``python -m smt_pipeline`` (``GEMINI_API_KEY``, etc.).

Skip policy: does not re-run if ``<bundle_out_dir>/<bundle_id>.json`` exists with
``pipeline_status == "committed"`` (success). Failed runs can be retried without ``--force-rerun``.

Handoffs are discovered from ``bundles/wfm_artifacts/hard_*_*.json`` (default). With
``--use-batch-order`` (default), order follows ``wfm_orchestration/wfm_hard_batch_curated.json``;
missing ids (e.g. one failed WFM run) are skipped automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]  # smt/smt_pipeline/ -> repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_HANDOFF_DIR = _REPO / "bundles" / "wfm_artifacts"
_DEFAULT_BATCH_JSON = _REPO / "wfm_orchestration" / "wfm_hard_batch_curated.json"
_DEFAULT_POLICY_DIR = _REPO / "bundles" / "smt_from_wfm" / "policies"
_DEFAULT_BUNDLE_OUT = _REPO / "bundles" / "smt_from_wfm"


def _find_handoff_for_example(handoff_dir: Path, ex_id: str) -> Path | None:
    prefix = f"hard_{ex_id.replace('-', '_')}_"
    matches = sorted(handoff_dir.glob(f"{prefix}*.json"))
    if not matches:
        return None
    return matches[-1]


def _discover_handoffs_glob(handoff_dir: Path, pattern: str) -> list[Path]:
    return sorted(handoff_dir.glob(pattern))


def _bundle_id_from_handoff(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    bid = data.get("bundle_id")
    if not bid:
        raise ValueError(f"Missing bundle_id in {path}")
    return str(bid)


def _is_pipeline_committed(bundle_out_dir: Path, bundle_id: str) -> bool:
    p = bundle_out_dir / f"{bundle_id}.json"
    if not p.is_file():
        return False
    rec = json.loads(p.read_text(encoding="utf-8"))
    return rec.get("pipeline_status") == "committed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Batch smt_pipeline on WFM handoffs: one policy file per bundle, resume + delay."
    )
    ap.add_argument(
        "--handoff-dir",
        type=Path,
        default=_DEFAULT_HANDOFF_DIR,
        help="Directory containing hard_*_*.json WFM handoffs.",
    )
    ap.add_argument(
        "--glob",
        type=str,
        default="hard_*.json",
        help="When not using batch order: glob under --handoff-dir (default: hard_*.json).",
    )
    ap.add_argument(
        "--use-batch-order",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Order runs using example_ids from --batch-json (default: true).",
    )
    ap.add_argument(
        "--batch-json",
        type=Path,
        default=_DEFAULT_BATCH_JSON,
        help="Curated batch list (example_ids) for ordering; missing handoffs are skipped.",
    )
    ap.add_argument(
        "--policy-dir",
        type=Path,
        default=_DEFAULT_POLICY_DIR,
        help="Directory for per-handoff policy_model.smt2 files (<handoff_stem>.smt2).",
    )
    ap.add_argument(
        "--bundle-out-dir",
        type=Path,
        default=_DEFAULT_BUNDLE_OUT,
        help="Pipeline bundle records and logs (same as smt_pipeline --out-bundle-dir).",
    )
    ap.add_argument(
        "--delay-sec",
        type=float,
        default=None,
        help="Sleep between runs (default: env SMT_BATCH_DELAY_SEC or 30).",
    )
    ap.add_argument(
        "--force-rerun",
        action="store_true",
        help="Ignore committed bundle records and re-run all discovered handoffs.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only (no Gemini, no writes).",
    )
    args = ap.parse_args(argv)

    delay = args.delay_sec
    if delay is None:
        delay = float(os.environ.get("SMT_BATCH_DELAY_SEC", "30"))

    handoff_dir = args.handoff_dir.resolve()
    if not handoff_dir.is_dir():
        print(f"error: handoff dir not found: {handoff_dir}", file=sys.stderr)
        return 2

    handoffs: list[tuple[Path, str | None]] = []
    if args.use_batch_order:
        if not args.batch_json.is_file():
            print(f"error: batch json not found: {args.batch_json}", file=sys.stderr)
            return 2
        raw = json.loads(args.batch_json.read_text(encoding="utf-8"))
        for ex_id in raw.get("example_ids") or []:
            hp = _find_handoff_for_example(handoff_dir, ex_id)
            if hp is None:
                print(f"[batch] No WFM handoff for example_id={ex_id} (skipped).", flush=True)
                continue
            handoffs.append((hp.resolve(), ex_id))
    else:
        for hp in _discover_handoffs_glob(handoff_dir, args.glob):
            handoffs.append((hp.resolve(), None))

    if not handoffs:
        print("error: no handoff JSON files to process.", file=sys.stderr)
        return 2

    policy_dir = args.policy_dir.resolve()
    bundle_out_dir = args.bundle_out_dir.resolve()

    # Build run list with skip-existing
    to_run: list[tuple[Path, str | None]] = []
    skipped_done: list[str] = []
    for hp, ex_id in handoffs:
        try:
            bid = _bundle_id_from_handoff(hp)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        label = ex_id or hp.name
        if not args.force_rerun and _is_pipeline_committed(bundle_out_dir, bid):
            skipped_done.append(f"{label} (bundle_id={bid})")
            continue
        to_run.append((hp, ex_id))

    if skipped_done:
        print(
            f"[batch] Skipping {len(skipped_done)} already-committed pipeline run(s):\n  "
            + "\n  ".join(skipped_done)
            + "\n",
            flush=True,
        )

    if args.dry_run:
        print(f"handoff_dir={handoff_dir}")
        print(f"policy_dir={policy_dir}")
        print(f"bundle_out_dir={bundle_out_dir}")
        print(f"delay_sec={delay}")
        print(f"to_run={len(to_run)}  (of {len(handoffs)} handoffs in plan)")
        for hp, ex_id in to_run:
            pol = policy_dir / f"{hp.stem}.smt2"
            print(f"  run  example_id={ex_id or '-'}  handoff={hp.name}  policy={pol.name}")
        return 0

    if not to_run:
        print("[batch] Nothing to run. Use --force-rerun to redo committed bundles.")
        return 0

    from smt_pipeline.config import smt_config_from_env
    from smt_pipeline.pipeline import run_smt_pipeline

    policy_dir.mkdir(parents=True, exist_ok=True)
    bundle_out_dir.mkdir(parents=True, exist_ok=True)
    cfg = smt_config_from_env()

    failures: list[tuple[str, str]] = []
    for j, (hp, ex_id) in enumerate(to_run):
        if j > 0:
            print(f"\n[batch] Sleeping {delay}s before next handoff...\n", flush=True)
            time.sleep(delay)

        policy_path = policy_dir / f"{hp.stem}.smt2"
        label = ex_id or hp.stem
        print(
            f"\n========== SMT batch {j + 1}/{len(to_run)}  "
            f"example_id={label}  handoff={hp.name} ==========\n",
            flush=True,
        )
        res = run_smt_pipeline(
            handoff_path=hp,
            policy_model_path=policy_path,
            bundle_out_dir=bundle_out_dir,
            cfg=cfg,
        )
        if res.status != "success":
            failures.append((label, res.failure_reason or "failed"))
            print(f"[batch] FAILED: {label}  ({res.failure_reason})", file=sys.stderr)

    if failures:
        print("\n[batch] Completed with failures:", file=sys.stderr)
        for label, msg in failures:
            print(f"  {label}: {msg}", file=sys.stderr)
        return 1

    print("\n[batch] All scheduled SMT runs finished OK.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
