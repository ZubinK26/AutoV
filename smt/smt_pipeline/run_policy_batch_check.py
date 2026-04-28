"""
Run Z3 check-sat and (if UNSAT) unsat-core extraction on every ``*.smt2`` under a directory.

Usage (from repo root)::

  python -m smt_pipeline.run_policy_batch_check
  python -m smt_pipeline.run_policy_batch_check --policy-dir bundles/smt_from_wfm/policies --out-json bundles/smt_from_wfm/sat_check_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]  # smt/smt_pipeline/ -> repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_POLICY_DIR = _REPO / "bundles" / "smt_from_wfm" / "policies"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SAT + unsat core for all policy .smt2 files in a folder.")
    ap.add_argument(
        "--policy-dir",
        type=Path,
        default=_DEFAULT_POLICY_DIR,
        help="Directory containing policy_model *.smt2 files.",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Write combined JSON report (optional).",
    )
    args = ap.parse_args(argv)

    d = args.policy_dir.resolve()
    if not d.is_dir():
        print(f"error: not a directory: {d}", file=sys.stderr)
        return 2

    from smt_pipeline.unsat_core import analyze_policy_file, report_to_jsonable

    files = sorted(d.glob("*.smt2"))
    if not files:
        print(f"error: no .smt2 files in {d}", file=sys.stderr)
        return 2

    report: dict[str, object] = {}
    exit_code = 0
    for p in files:
        try:
            r = analyze_policy_file(p)
            report[p.name] = report_to_jsonable(r)
            if r.sat_result == "unknown":
                exit_code = 2
        except Exception as e:
            report[p.name] = {"error": str(e)}
            exit_code = 2

    summary = {
        "policy_dir": str(d),
        "count": len(files),
        "sat": sum(1 for v in report.values() if isinstance(v, dict) and v.get("sat_result") == "sat"),
        "unsat": sum(1 for v in report.values() if isinstance(v, dict) and v.get("sat_result") == "unsat"),
        "unknown": sum(1 for v in report.values() if isinstance(v, dict) and v.get("sat_result") == "unknown"),
        "errors": sum(1 for v in report.values() if isinstance(v, dict) and "error" in v),
        "files": report,
    }

    print(json.dumps(summary, indent=2))
    if args.out_json is not None:
        out = args.out_json.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nWrote {out}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
