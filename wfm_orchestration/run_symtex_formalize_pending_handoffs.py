"""
Run ``asp_pipeline`` only on **SymTex ground-truth** WFM handoffs that are not yet formalized.

Skips:
- Non-``symtex_batch_*`` handoffs
- Handoffs whose text does not match the SymTex benchmark banner (see ``symtex_ground_truth_utils``)
- Handoffs that already have a **committed** record under ``--bundle-out-dir``
- Optional: with ``--only-if-baseline-committed-in``, only handoffs that already have a
  committed record in that **baseline** directory (use with a new ``--bundle-out-dir`` to
  re-formalize the same SymTex set with a different ``--formalizer-prompt`` for comparison)

If there is nothing to run, exits 0 (pytest can treat as skip when used with dry-run).

From repo root::

  python -m wfm_orchestration.run_symtex_formalize_pending_handoffs --dry-run
  python -m wfm_orchestration.run_symtex_formalize_pending_handoffs --delay-sec 5
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_HANDOFF = _REPO / "bundles" / "wfm_artifacts"
_DEFAULT_POLICY = _REPO / "bundles" / "asp_from_wfm" / "policies"
_DEFAULT_OUT = _REPO / "bundles" / "asp_from_wfm"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Formalize SymTex WFM handoffs that lack a committed asp_pipeline bundle."
    )
    p.add_argument("--handoff-dir", type=Path, default=_DEFAULT_HANDOFF)
    p.add_argument("--glob", type=str, default="*.json")
    p.add_argument("--policy-dir", type=Path, default=_DEFAULT_POLICY)
    p.add_argument("--bundle-out-dir", type=Path, default=_DEFAULT_OUT)
    p.add_argument(
        "--delay-sec",
        type=float,
        default=None,
        help="Seconds between handoffs (default: env SYMTE_FORMALIZE_DELAY_SEC or 5).",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="On formalizer/503/API errors, log and process remaining handoffs; exit 1 if any failed. Re-run the same command to retry only not-yet-committed (pending) items.",
    )
    p.add_argument(
        "--formalizer-prompt",
        type=str,
        default=None,
        help="Basename under asp_pipeline/prompts/ (default: env ASP_PIPELINE_FORMALIZER_PROMPT or formalizer_new.md).",
    )
    p.add_argument(
        "--only-if-baseline-committed-in",
        type=Path,
        default=None,
        help=(
            "Only formalize SymTex handoffs whose bundle_id already has a committed asp_clincon "
            "record in this directory (e.g. bundles/asp_from_wfm). Use with a *new* "
            "--bundle-out-dir to re-run the same successful baseline set with a new --formalizer-prompt."
        ),
    )
    args = p.parse_args(argv)

    delay = args.delay_sec
    if delay is None:
        delay = float(os.environ.get("SYMTE_FORMALIZE_DELAY_SEC", "5"))

    from wfm_orchestration.symtex_ground_truth_utils import pending_formalize_symtex_handoffs

    hdir = args.handoff_dir.resolve()
    bdir = args.bundle_out_dir.resolve()
    pdir = args.policy_dir.resolve()

    to_run = pending_formalize_symtex_handoffs(
        repo_root=_REPO,
        handoff_dir=hdir,
        bundle_out_dir=bdir,
        glob=args.glob,
        only_if_baseline_committed_in=args.only_if_baseline_committed_in,
    )
    if args.dry_run:
        fcfg = args.formalizer_prompt or "(env/default formalizer_new.md)"
        bline = args.only_if_baseline_committed_in or ""
        bline = f"  baseline={bline}" if bline else ""
        print(
            f"handoff_dir={hdir}  policy_dir={pdir}  bundle_out={bdir}  "
            f"delay_sec={delay}  formalizer_prompt={fcfg}{bline}  "
            f"to_run={len(to_run)} (symtex ground-truth, not yet committed formalization)"
        )
        for hp in to_run:
            print(f"  {hp.name}")
        if not to_run:
            print("  (none: all matching SymTex handoffs already have committed asp pipeline, or no SymTex handoffs).")
        return 0
    if not to_run:
        print(
            "[symtex formalize] Nothing to do: no SymTex-benchmark handoffs need formalization.\n"
            "  (Either no symtex_batch_ handoffs, or all already have committed bundles/asp_from_wfm/<id>.json.)\n"
        )
        return 0

    from wfm_orchestration.e2e_context import load_dotenv_for_e2e

    load_dotenv_for_e2e()
    from asp_pipeline.config import asp_config_from_env
    from asp_pipeline.pipeline import run_asp_pipeline

    pdir.mkdir(parents=True, exist_ok=True)
    bdir.mkdir(parents=True, exist_ok=True)
    cfg = asp_config_from_env()
    if args.formalizer_prompt:
        cfg = replace(cfg, formalizer_prompt=args.formalizer_prompt)
    fail: list[str] = []
    for j, hp in enumerate(to_run):
        if j > 0 and delay > 0:
            time.sleep(delay)
        pol = pdir / f"{hp.stem}.lp"
        print(f"\n========== SymTex formalize {j + 1}/{len(to_run)}  {hp.name} ==========\n", flush=True)
        r = run_asp_pipeline(handoff_path=hp, policy_model_path=pol, bundle_out_dir=bdir, cfg=cfg)
        if r.status != "success":
            line = f"{hp.name}: {r.failure_reason or r.status or 'failed'}"
            fail.append(line)
            if not args.continue_on_failure:
                print("Failures:", file=sys.stderr)
                print(" ", line, file=sys.stderr)
                return 1

    if fail:
        print("Failures (re-run the same command after fixing API/503; already-committed are skipped):", file=sys.stderr)
        for f in fail:
            print(" ", f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
