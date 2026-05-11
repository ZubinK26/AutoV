"""NagV CLI: NL rules → WFM (SMT profile) → formalizer/critic ↔ Nagini."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_import_paths() -> tuple[Path, Path]:
    """``NagV/`` on path for ``nagv``; repo root for ``wfm_orchestration``."""
    nagv_pkg = Path(__file__).resolve().parent
    nagv_dir = nagv_pkg.parent
    repo_root = nagv_dir.parent
    if str(nagv_dir) not in sys.path:
        sys.path.insert(0, str(nagv_dir))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return repo_root, nagv_dir


def main(argv: list[str] | None = None) -> int:
    repo_root, _nagv_dir = _ensure_import_paths()

    from nagv.pipeline import run_nagv
    from nagv.runtime_env import apply_nagv_gemini_defaults

    apply_nagv_gemini_defaults()

    parser = argparse.ArgumentParser(
        description="NagV: WFM (SMT) -> Z3 feasibility -> semantic critic -> Z3 verify (sat)"
    )
    parser.add_argument(
        "--nl-file",
        type=Path,
        help="UTF-8 NL ruleset (one rule per non-empty line). Required unless --skip-wfm.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Run directory (wfm_handoffs/, nl_chunk_progress.json, candidates/, final.py, etc.).",
    )
    parser.add_argument(
        "--skip-wfm",
        action="store_true",
        help="Reuse existing WFM artifacts under work-dir (aggregates PASS+REWRITE Agent3 lines; blocks on OUT_OF_SCOPE etc.).",
    )
    parser.add_argument(
        "--reset-wfm-progress",
        action="store_true",
        help="Restart nl_chunk_progress from rule 0 (only when WFM runs).",
    )
    parser.add_argument(
        "--rules-per-chunk",
        type=int,
        default=10,
        help="WFM chunk size (default 10).",
    )
    parser.add_argument(
        "--z3-timeout",
        "--nagini-timeout",
        type=int,
        default=120,
        dest="solver_timeout_sec",
        help="Subprocess timeout seconds for Z3 driver (default 120). --nagini-timeout is a deprecated alias.",
    )

    args = parser.parse_args(argv)
    repo = repo_root.resolve()

    if not args.skip_wfm and args.nl_file is None:
        print("error: --nl-file is required when not using --skip-wfm", file=sys.stderr)
        return 2

    result = run_nagv(
        repo_root=repo,
        nl_file=args.nl_file,
        work_dir=args.work_dir,
        skip_wfm=args.skip_wfm,
        rules_per_chunk=args.rules_per_chunk,
        reset_wfm_progress=args.reset_wfm_progress,
        solver_timeout_sec=args.solver_timeout_sec,
    )

    print(f"\nOutcome: {result.outcome}\n{result.message}\n")
    if result.final_py:
        print(f"final.py: {result.final_py}\n")

    if result.outcome == "success":
        return 0
    if result.outcome in (
        "error_config",
        "error_wfm",
        "error_z3_env",
        "error_z3_tool",
        "error_timeout",
    ):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
