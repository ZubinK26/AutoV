"""
Batch ``asp_pipeline`` on WFM handoff JSONs (resume on committed bundle record).

From repo root::

  python -m asp_pipeline.run_wfm_handoff_batch --handoff-dir bundles/wfm_artifacts --glob "symtex_*.json"
  python -m asp_pipeline.run_wfm_handoff_batch --dry-run

Default output: ``bundles/asp_from_wfm/`` (records +``policies/<stem>.lp``).

To **A/B another formalizer** (e.g. legacy template), use e.g.::

  --formalizer-prompt formalizer.md  --policy-dir bundles/asp_experiment/policies  --bundle-out-dir bundles/asp_experiment

Committed JSON records include ``formalizer_prompt`` and ``formalizer_prompt_sha256`` for comparison.
"""

from __future__ import annotations

import argparse
import json
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


def _bundle_id(p: Path) -> str:
    d = json.loads(p.read_text(encoding="utf-8"))
    b = d.get("bundle_id")
    if not b:
        raise ValueError(f"Missing bundle_id in {p}")
    return str(b)


def _is_committed(out_dir: Path, bundle_id: str) -> bool:
    f = out_dir / f"{bundle_id}.json"
    if not f.is_file():
        return False
    r = json.loads(f.read_text(encoding="utf-8"))
    return r.get("pipeline_status") == "committed" and r.get("pipeline_kind") == "asp_clincon"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Batch asp_pipeline on WFM handoff JSON files.")
    ap.add_argument("--handoff-dir", type=Path, default=_DEFAULT_HANDOFF)
    ap.add_argument("--glob", type=str, default="*.json")
    ap.add_argument("--policy-dir", type=Path, default=_DEFAULT_POLICY)
    ap.add_argument("--bundle-out-dir", type=Path, default=_DEFAULT_OUT)
    ap.add_argument(
        "--delay-sec",
        type=float,
        default=None,
        help="Delay between handoffs (default: env ASP_BATCH_DELAY_SEC or 30).",
    )
    ap.add_argument("--force-rerun", action="store_true")
    ap.add_argument(
        "--formalizer-prompt",
        type=str,
        default=None,
        help="Basename under asp_pipeline/prompts/ (default: env ASP_PIPELINE_FORMALIZER_PROMPT or formalizer_new.md).",
    )
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    delay = a.delay_sec if a.delay_sec is not None else float(os.environ.get("ASP_BATCH_DELAY_SEC", "30"))

    hdir = a.handoff_dir.resolve()
    if not hdir.is_dir():
        print(f"error: {hdir} not a directory", file=sys.stderr)
        return 2
    handoffs = sorted(hdir.glob(a.glob))
    if not handoffs:
        print(f"error: no files matching {a.glob!r} under {hdir}", file=sys.stderr)
        return 2
    pdir = a.policy_dir.resolve()
    bdir = a.bundle_out_dir.resolve()

    to_run: list[Path] = []
    for hp in handoffs:
        if "manifest" in hp.name:
            continue
        try:
            bid = _bundle_id(hp)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"warning: skip {hp.name} ({e})", file=sys.stderr)
            continue
        if not a.force_rerun and _is_committed(bdir, bid):
            print(f"[batch] skip committed {bid} ({hp.name})", flush=True)
            continue
        to_run.append(hp)

    if a.dry_run:
        print(f"handoff_dir={hdir}  n={len(to_run)}  policy_dir={pdir}  out={bdir}  delay={delay}")
        for hp in to_run:
            print(f"  {hp.name}  ->  {(pdir / f'{hp.stem}.lp').name}")
        return 0
    if not to_run:
        print("[batch] nothing to run (all committed? use --force-rerun)")
        return 0

    from asp_pipeline.config import asp_config_from_env
    from asp_pipeline.pipeline import run_asp_pipeline

    pdir.mkdir(parents=True, exist_ok=True)
    bdir.mkdir(parents=True, exist_ok=True)
    cfg = asp_config_from_env()
    if a.formalizer_prompt:
        cfg = replace(cfg, formalizer_prompt=a.formalizer_prompt)
    fail: list[str] = []
    for j, hp in enumerate(to_run):
        if j > 0:
            time.sleep(delay)
        pol = pdir / f"{hp.stem}.lp"
        print(f"\n========== ASP batch {j + 1}/{len(to_run)}  {hp.name} ==========\n", flush=True)
        r = run_asp_pipeline(handoff_path=hp, policy_model_path=pol, bundle_out_dir=bdir, cfg=cfg)
        if r.status != "success":
            fail.append(f"{hp.name}: {r.failure_reason or 'failed'}")

    if fail:
        print("Failures:", file=sys.stderr)
        for f in fail:
            print(" ", f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
