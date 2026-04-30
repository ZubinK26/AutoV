from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentsim.runtime.policy_consistency import (
    build_consistency_report,
    deployment_should_fail,
    policy_text_from_path,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pre-deployment policy consistency check → consistency_report.json (agentsim/03).",
    )
    parser.add_argument(
        "policy_smt2",
        type=Path,
        help="Path to policy .smt2 file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to this path (default: stdout only)",
    )
    parser.add_argument(
        "--pairwise",
        action="store_true",
        help="Run optional pairwise rule analysis (expensive).",
    )
    args = parser.parse_args(argv)

    text = policy_text_from_path(args.policy_smt2)
    report = build_consistency_report(text, run_pairwise=args.pairwise)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_report(args.output, report)
    else:
        sys.stdout.write(report.to_json())

    return 1 if deployment_should_fail(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
