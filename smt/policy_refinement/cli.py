"""CLI: NL-aligned policy refinement (assessor + implementer + repair)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .run import run_assess_and_refine


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Post-formalization policy refinement (see dev_plans/dev_plan_policy_nl_refinement_agents_v1.md)."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ar = sub.add_parser("assess-and-refine", help="Run assessor → implementer → SAT/parse/critic repair")
    ar.add_argument("--policy", type=Path, required=True, help="Committed policy_model.smt2")
    ar.add_argument("--nl", type=Path, required=True, help="Canonical NL rules file (one rule per line)")
    ar.add_argument("--out-dir", type=Path, required=True, help="Run output directory (created if missing)")
    ar.add_argument("--run-id", type=str, default=None, help="Opaque run id (default: timestamp-based)")
    ar.add_argument(
        "--skip-assessor",
        action="store_true",
        help="Load assessment.json from --assessment or <out-dir>/assessment.json",
    )
    ar.add_argument(
        "--assessment",
        type=Path,
        default=None,
        help="Path to existing assessment.json when using --skip-assessor",
    )

    args = p.parse_args(argv)

    if args.cmd == "assess-and-refine":
        res = run_assess_and_refine(
            policy_path=args.policy,
            nl_path=args.nl,
            out_dir=args.out_dir,
            run_id=args.run_id,
            skip_assessor=args.skip_assessor,
            assessment_path=args.assessment,
        )
        print(json.dumps({"status": res.status, "failure_reason": res.failure_reason, "out_dir": str(res.out_dir)}, indent=2))
        return 0 if res.status == "success" else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
