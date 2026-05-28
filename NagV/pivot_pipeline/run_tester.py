"""CLI entry to run Pivot Tester (NL ↔ linearized IR) on an existing work directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Run Pivot Tester on an existing pivot work directory: "
            "processed NL vs linearized IR (per-rule content alignment). "
            "Requires rules_extracted.json and processed NL in the work dir "
            "(rules_source.txt, phase0_normalized_nl.txt, or nl_after_extract_rewrites.txt). "
            "Does not run WFM, extract, or pivot critic."
        ),
        epilog=(
            "Example:\n"
            "  pivot-tester --work-dir NagV/exports/pivot_runs/my_run "
            "--input path/to/original.nl\n\n"
            "Equivalent main CLI:\n"
            "  pivot-pipeline --work-dir ... --input ... --skip-phase0 "
            "--rules-json <work-dir>/rules_extracted.json --with-tester"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--work-dir", required=True, type=Path)
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Original nl_source path (policy id / resolution); same as pivot-pipeline CLI",
    )
    p.add_argument(
        "--rules-json",
        type=Path,
        default=None,
        help="Defaults to <work-dir>/rules_extracted.json",
    )
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--fail-on-tester-findings",
        action="store_true",
        help="Exit non-zero when tester verdict is 'issues'",
    )
    p.add_argument(
        "--with-test-repair",
        action="store_true",
        help="Allow Test-Repairer when interactive gate chooses REPAIR.",
    )
    p.add_argument(
        "--interactive-tester",
        action="store_true",
        help="Enable per-finding triage + REPAIR / PROCEED_INCOMPLETE gate on tester issues.",
    )
    p.add_argument(
        "--interactive-policy",
        action="store_true",
        help="Same as pivot-pipeline: enables tester gate together with other policy gates.",
    )
    p.add_argument(
        "--resume-tester-repair",
        action="store_true",
        help="Skip Pivot Tester; resume from tester_repair_handoff.json approved findings.",
    )
    p.add_argument(
        "--retriage-tester",
        action="store_true",
        help="With --resume-tester-repair, re-run triage (a/i) instead of saved approvals.",
    )
    p.add_argument("--fail-on-precheck-warnings", action="store_true")
    p.add_argument("--fail-on-varprod-trigger", action="store_true")
    p.add_argument("--no-llm", action="store_true", help="Tester requires LLM; this flag is rejected")
    p.add_argument("--skip-registry", action="store_true")
    args = p.parse_args(argv)

    if args.no_llm:
        print("error: Pivot Tester requires LLM calls; omit --no-llm.", file=sys.stderr)
        return 1
    if args.resume_tester_repair and not args.with_test_repair:
        print("error: --resume-tester-repair requires --with-test-repair", file=sys.stderr)
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
        fail_on_tester_findings=args.fail_on_tester_findings,
        with_test_repair=args.with_test_repair,
        interactive_tester=args.interactive_tester,
        resume_tester_repair=args.resume_tester_repair,
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
    if summary.get("precheck_ok") is False and args.fail_on_precheck_warnings:
        return 2
    if summary.get("varprod_trigger_ok") is False and args.fail_on_varprod_trigger:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
