"""CLI: WFM handoff -> ClinCon ``.lp`` (``python -m asp_pipeline``)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

from asp_pipeline.config import asp_config_from_env
from asp_pipeline.pipeline import run_asp_pipeline


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="WFM handoff -> ClinCon / Clingo .lp (parse/ground + critic + commit).")
    p.add_argument("--handoff", required=True, type=Path, help="WFM HandoffBundle JSON (registry_persistence_v1).")
    p.add_argument(
        "--policy-model",
        type=Path,
        default=Path("policy_model.lp"),
        help="Target policy .lp (default: ./policy_model.lp).",
    )
    p.add_argument(
        "--out-bundle-dir",
        type=Path,
        default=Path("bundles/asp_from_wfm"),
        help="Per-bundle JSON record and .log.jsonl (default: ./bundles/asp_from_wfm).",
    )
    p.add_argument(
        "--formalizer-prompt",
        type=str,
        default=None,
        help="Basename under asp_pipeline/prompts/ (default: env ASP_PIPELINE_FORMALIZER_PROMPT or formalizer_new.md).",
    )
    args = p.parse_args(argv)
    cfg = asp_config_from_env()
    if args.formalizer_prompt:
        cfg = replace(cfg, formalizer_prompt=args.formalizer_prompt)
    res = run_asp_pipeline(
        handoff_path=args.handoff,
        policy_model_path=args.policy_model,
        bundle_out_dir=args.out_bundle_dir,
        cfg=cfg,
    )
    print(json.dumps(asdict(res), indent=2, ensure_ascii=False))
    return 0 if res.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
