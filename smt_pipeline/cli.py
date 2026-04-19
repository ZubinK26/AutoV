"""CLI for `smt_pipeline` — WFM handoff → SMT-LIB policy commit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dataclasses import asdict

from .config import smt_config_from_env
from .pipeline import run_smt_pipeline


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="NL→SMT-LIB pipeline (control_flow v3)")
    p.add_argument("--handoff", required=True, type=Path, help="WFM handoff JSON (registry_persistence_v1)")
    p.add_argument(
        "--policy-model",
        type=Path,
        default=Path("policy_model.smt2"),
        help="Path to policy_model.smt2 (default: ./policy_model.smt2)",
    )
    p.add_argument(
        "--out-bundle-dir",
        type=Path,
        default=Path("bundles"),
        help="Directory for bundles/{bundle_id}.json and .log.jsonl",
    )
    args = p.parse_args(argv)

    cfg = smt_config_from_env()
    res = run_smt_pipeline(
        handoff_path=args.handoff,
        policy_model_path=args.policy_model,
        bundle_out_dir=args.out_bundle_dir,
        cfg=cfg,
    )
    print(json.dumps(asdict(res), indent=2))
    return 0 if res.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
