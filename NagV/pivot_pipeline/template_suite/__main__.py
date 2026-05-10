"""CLI: python -m pivot_pipeline.template_suite"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pivot_pipeline.template_suite.run import run_template_suite


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run executable template tests against a pivot policy (Z3).")
    p.add_argument("--suite", type=Path, required=True, help="Suite JSON (schema_version + instances).")
    p.add_argument(
        "--rules-extracted",
        type=Path,
        required=True,
        help="rules_extracted.json (policy_id + rules) from a pivot work directory.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write template_run_report.json here (default: stdout only).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print JSON report to stdout (still writes --out if set).",
    )
    args = p.parse_args(argv)

    report = run_template_suite(
        suite_path=args.suite,
        rules_extracted_path=args.rules_extracted,
        out_report_path=args.out,
        write_report=args.out is not None,
    )
    if not args.quiet:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    s = report["summary"]
    if s.get("failed") or s.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
