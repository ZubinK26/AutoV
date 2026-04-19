"""CLI: SAT/UNSAT + unsat core for a committed ``policy_model.smt2``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .unsat_core import analyze_policy_file, report_to_jsonable


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run Z3 check-sat and (if unsat) unsat core on policy_model.smt2 (Rule-tagged asserts)."
    )
    p.add_argument(
        "policy_model",
        type=Path,
        nargs="?",
        default=Path("policy_model.smt2"),
        help="Path to policy_model.smt2 (default: ./policy_model.smt2)",
    )
    args = p.parse_args(argv)
    r = analyze_policy_file(args.policy_model)
    print(json.dumps(report_to_jsonable(r), indent=2))
    return 0 if r.sat_result != "unknown" else 2


if __name__ == "__main__":
    raise SystemExit(main())
