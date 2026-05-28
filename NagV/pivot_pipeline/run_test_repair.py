"""CLI entry to resume Test-Repairer from saved tester handoff (no Pivot Tester LLM)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Resume Test-Repairer on an existing pivot work directory using "
            "tester_report.json and tester_repair_handoff.json (approved findings). "
            "Does not run Pivot Tester, WFM, extract, or pivot critic."
        ),
        epilog=(
            "Example:\n"
            "  pivot-test-repair --work-dir NagV/exports/pivot_runs/recruitment_16_temp_wfm "
            "--input path/to/latest.nl --interactive-tester\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--work-dir", required=True, type=Path)
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Original nl_source path (policy id); same as pivot-pipeline CLI",
    )
    p.add_argument(
        "--rules-json",
        type=Path,
        default=None,
        help="Defaults to <work-dir>/rules_extracted.json",
    )
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--retriage-tester",
        action="store_true",
        help="Re-run per-finding triage (a/i) instead of reusing handoff approvals.",
    )
    p.add_argument(
        "--interactive-tester",
        action="store_true",
        help="Enable REPAIR / PROCEED_INCOMPLETE gate (required for interactive repair).",
    )
    p.add_argument(
        "--interactive-policy",
        action="store_true",
        help="Same as pivot-pipeline: enables tester repair gate.",
    )
    p.add_argument("--fail-on-precheck-warnings", action="store_true")
    p.add_argument("--fail-on-varprod-trigger", action="store_true")
    p.add_argument("--no-llm", action="store_true", help="Test-Repairer requires LLM; rejected")
    p.add_argument("--skip-registry", action="store_true")
    args = p.parse_args(argv)

    if args.no_llm:
        print("error: Test-Repairer requires LLM calls; omit --no-llm.", file=sys.stderr)
        return 1
    if not args.interactive_tester and not args.interactive_policy:
        print(
            "error: pivot-test-repair requires --interactive-tester or --interactive-policy",
            file=sys.stderr,
        )
        return 1

    rules_json = args.rules_json or (args.work_dir / "rules_extracted.json")
    if not rules_json.is_file():
        print(f"rules JSON not found: {rules_json}", file=sys.stderr)
        return 1

    from pivot_pipeline.paths import resolve_existing_user_file
    from pivot_pipeline.run import run_pivot_pipeline

    nl_source = resolve_existing_user_file(args.input)

    summary = run_pivot_pipeline(
        repo_root=args.repo_root.resolve(),
        work_dir=args.work_dir,
        nl_source=nl_source,
        rules_json=rules_json,
        skip_phase0=True,
        reset_progress=False,
        rules_per_chunk=5,
        skip_critic=True,
        no_llm=False,
        skip_registry=args.skip_registry,
        extract_only=False,
        interactive_policy=args.interactive_policy,
        interactive_extract_abort=False,
        interactive_cross_coherence=False,
        with_tester=True,
        with_test_repair=True,
        fail_on_tester_findings=False,
        interactive_tester=args.interactive_tester,
        resume_tester_repair=True,
        retriage_tester=args.retriage_tester,
        repairer_max_rounds=0,
        with_cross_critic=False,
        with_cross_repair=False,
        cross_coherence_skip_critic_gate=False,
        fail_on_precheck_warnings=args.fail_on_precheck_warnings,
        fail_on_varprod_trigger=args.fail_on_varprod_trigger,
        input_fn=input,
        print_fn=print,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    outcome = summary.get("outcome", "")
    if outcome in ("blocked_tester", "blocked_tester_output_parse"):
        return 1
    if outcome.startswith("blocked"):
        return 3 if outcome == "blocked_test_repair_compile" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
