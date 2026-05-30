"""CLI: ``pivot-pipeline`` / ``python -m pivot_pipeline``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_script = Path(__file__).resolve()
_REPO = _script.parents[2]
_NAGV_ROOT = _script.parents[1]
for _p in (_REPO, _NAGV_ROOT):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from pivot_pipeline.paths import resolve_existing_user_file


def main(argv: list[str] | None = None) -> int:
    from registry_stage.llm.gemini_call import load_repo_dotenv

    load_repo_dotenv()

    p = argparse.ArgumentParser(description="Pivot policy pipeline (NL → WFM → JSON IR → Z3)")
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help=(
            "Source NL rules file (one rule per non-comment line). Relative paths use the current working "
            "directory; on Windows, a leading ``NagV/`` / ``nagv/`` segment is dropped when it would incorrectly "
            "resolve into the ``nagv`` package directory—prefer ``pivot_pipeline/inputs/...`` from the NagV root."
        ),
    )
    p.add_argument(
        "--work-dir",
        required=True,
        type=Path,
        help=(
            "Run output directory (progress, handoffs, extracts, Z3, summaries). Use a **different** path per "
            "``--input`` file so one policy run never overwrites another (e.g. ``.../pivot_runs/evaluation_...`` vs "
            "``.../pivot_runs/test_input_...``)."
        ),
    )
    p.add_argument("--repo-root", type=Path, default=_REPO, help="AutoV repo root")
    p.add_argument(
        "--skip-phase0",
        action="store_true",
        help=(
            "Skip pivot WFM. If work_dir/phase0_normalized_nl.txt exists and is non-empty, extract+later phases use "
            "that text (reuse completed Phase 0 / handoffs); otherwise raw --input. policy_id still comes from --input. "
            "Omits --reset-progress when re-running extract after a WFM-only success."
        ),
    )
    p.add_argument(
        "--reset-progress",
        action="store_true",
        help=(
            "Phase 0: delete nl_chunk_progress.json, clear work_dir/wfm_handoffs/, and reset pivot WFM sidecar "
            "files in --work-dir so the next run starts from rule 0 (use when you want a clean WFM pass). "
            "Also use when the NL file or --rules-per-chunk changed and the progress file would otherwise error."
        ),
    )
    p.add_argument("--rules-per-chunk", type=int, default=5)
    p.add_argument(
        "--rules-json",
        type=Path,
        default=None,
        help="Phase 1 output: {policy_id?, rules: [...]} (skips LLM extract when set and file exists)",
    )
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="When no usable --rules-json, abort instead of calling Gemini for extraction",
    )
    p.add_argument(
        "--skip-registry",
        action="store_true",
        help="After per-line extract, skip batched identifier registry + rewrite",
    )
    p.add_argument(
        "--extract-only",
        action="store_true",
        help="Stop after Phase 1 (writes rules_extracted.json); no compile/Z3/precheck/critic",
    )
    p.add_argument(
        "--with-critic",
        action="store_true",
        help=(
            "Run structured LLM critic (JSON): effective NL vs synthetic_en.md. "
            "On DRIFT with --interactive-policy, choose REPAIR (semantic Repairer_Piv), "
            "PROCEED_INCOMPLETE (writes critic_drift_handoff.json), or Enter to abort."
        ),
    )
    p.add_argument(
        "--with-tester",
        action="store_true",
        help=(
            "Per-rule processed NL vs linearized IR alignment (tester_report.json); "
            "JSON repair retries via PIVOT_TESTER_JSON_REPAIR_MAX; "
            "runs after precheck, before --with-critic when both are set."
        ),
    )
    p.add_argument(
        "--fail-on-tester-findings",
        action="store_true",
        help="When --with-tester and verdict is 'issues', exit blocked_tester (CI-style).",
    )
    p.add_argument(
        "--with-test-repair",
        action="store_true",
        help=(
            "Allow Test-Repairer when interactive tester gate chooses REPAIR "
            "(requires --with-tester and --interactive-tester or --interactive-policy)."
        ),
    )
    p.add_argument(
        "--interactive-tester",
        action="store_true",
        help=(
            "TTY prompts when Pivot Tester reports issues: per-finding approve/ignore triage, "
            "then REPAIR (Test-Repairer) or PROCEED_INCOMPLETE."
        ),
    )
    p.add_argument(
        "--resume-tester-repair",
        action="store_true",
        help=(
            "Skip Pivot Tester LLM; load tester_report.json + tester_repair_handoff.json "
            "(non-empty approved_finding_ids) and continue at REPAIR gate. Requires "
            "--with-test-repair and --interactive-tester or --interactive-policy."
        ),
    )
    p.add_argument(
        "--retriage-tester",
        action="store_true",
        help="With --resume-tester-repair, re-run per-finding triage instead of reusing approvals.",
    )
    p.add_argument(
        "--repairer-max-rounds",
        type=int,
        default=2,
        help="Max structural Repairer_Piv rounds after load_rules_and_compile failure (default 2). Use 0 to disable.",
    )
    p.add_argument(
        "--interactive-extract-abort",
        action="store_true",
        help=(
            "Alias for extract ABORT rewrite loop; use --interactive-policy for full gates (WFM coverage, critic, …)"
        ),
    )
    p.add_argument(
        "--interactive-policy",
        action="store_true",
        help=(
            "TTY prompts after Phase 0: per-chunk WFM **line coverage** repair (scope rewrite + retry); "
            "block when WFM rule count != source unless you type PROCEED_INCOMPLETE; "
            "extract ABORT rewrite rounds (see PIVOT_SCOPE_REWRITE_MAX_PROPOSALS_PER_LINE) then abort vs drop; "
            "critic DRIFT: type REPAIR for semantic Repairer_Piv, or PROCEED_INCOMPLETE to waive. "
            "(Phase 0 still prompts to **accept each WFM handoff** before it is saved, unless tools use internal "
            "one-line WFM with auto-accept.) WFM chunk attempts: PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS (default 3)."
        ),
    )
    p.add_argument(
        "--interactive-cross-coherence",
        action="store_true",
        help=(
            "TTY prompts when CrossCritic reports ISSUES: triage findings (accept all or "
            "disagree by number), then REPAIR with --with-cross-repair, or PROCEED_INCOMPLETE."
        ),
    )
    p.add_argument(
        "--with-cross-critic",
        action="store_true",
        help=(
            "After semantic critic PASS (unless --cross-coherence-skip-critic-gate), run CrossCritic on "
            "processed NL + linearized rules. Requires LLM (omit --no-llm)."
        ),
    )
    p.add_argument(
        "--with-cross-repair",
        action="store_true",
        help="With interactive cross gates, allow CrossRepairer when CrossCritic reports ISSUES.",
    )
    p.add_argument(
        "--cross-coherence-skip-critic-gate",
        action="store_true",
        help="Allow CrossCritic when critic was skipped or did not PASS (development / hand reuse).",
    )
    p.add_argument(
        "--fail-on-precheck-warnings",
        action="store_true",
        help="Abort before later phases when heuristic precheck reports issues (writes blocked_precheck).",
    )
    p.add_argument(
        "--fail-on-varprod-trigger",
        action="store_true",
        help=(
            "Abort when varprod trigger IR check fails (both varprod factors must appear in "
            "LOGICAL_IMPLICATION trigger unless rule id is in PIVOT_VARPROD_TRIGGER_SKIP_RULE_IDS)."
        ),
    )
    p.add_argument(
        "--with-template-generator",
        action="store_true",
        help=(
            "After Z3/precheck: call Gemini to author template_suite_generated.json from policy context, "
            "then run executable template tests (writes template_run_report.json). Incompatible with --no-llm. "
            "Falls back to --template-suite if set when generator is skipped."
        ),
    )
    p.add_argument(
        "--template-suite",
        type=Path,
        default=None,
        help=(
            "After Z3/precheck: run executable template tests from this suite JSON (no LLM). "
            "If also --with-template-generator and LLM is enabled, generated suite wins; if generator is skipped "
            "(--no-llm), this file is used when provided."
        ),
    )
    p.add_argument(
        "--with-template-repair",
        action="store_true",
        help=(
            "After template suite run: diagnose fail/inconclusive tests, interactive triage, "
            "Template Repairer on approved policy_ir findings, re-verify tester/critic/cross/suite."
        ),
    )
    p.add_argument(
        "--interactive-template-suite",
        action="store_true",
        help="Enable template diagnostic triage and REPAIR gate (or use --interactive-policy).",
    )
    p.add_argument(
        "--fail-on-template-findings",
        action="store_true",
        help="Exit blocked_template when template suite has fail/inconclusive and not waived.",
    )
    p.add_argument(
        "--with-external-tester",
        action="store_true",
        help=(
            "After template suite (if any): fill world from --external-source via provenance agents, "
            "blind review, then run one scenario Z3 test (full policy SAT + CWA defaults; "
            "writes external_tester_run_report.json)."
        ),
    )
    p.add_argument(
        "--external-source",
        type=Path,
        default=None,
        help="Unstructured text file or numbered JSON envelope for --with-external-tester.",
    )
    p.add_argument(
        "--external-instance-id",
        default="ext_001",
        help="Instance id for external tester output (default ext_001).",
    )
    p.add_argument(
        "--external-test-mode",
        choices=("scenario", "decision_query"),
        default=None,
        help=(
            "External tester executable: scenario (default) = policy∧world SAT with not_found→false/0; "
            "decision_query = legacy single-rule probe (omits not_found from world)."
        ),
    )
    p.add_argument(
        "--external-fill-orchestration",
        choices=("v2", "v3"),
        default=None,
        help="v3 (default): chunked two-phase fill + completeness critic; v2: monolithic fill.",
    )
    p.add_argument(
        "--external-query-rule",
        default=None,
        help="Legacy decision_query only: force query.rule_id for fill agent.",
    )
    p.add_argument(
        "--require-prior-critics",
        action="store_true",
        help=(
            "With --with-external-tester: abort if tester/critic/cross reports are not clean "
            "(when those artifacts exist in work_dir)."
        ),
    )
    p.add_argument(
        "--no-vnext-lowering",
        action="store_true",
        help=(
            "Debug: skip expand_rules_to_core before compile (fails if rules still contain vNext templates). "
            "Default lowers INT_RANGE, K_OF_N, SUM_THRESHOLD, etc. to core IR."
        ),
    )
    p.add_argument(
        "--save-golden",
        action="store_true",
        help=(
            "After this run, replace pivot_pipeline/golden_test_run/ with a full copy of --work-dir "
            "(WFM handoffs under work/, extracts, Z3, critic, traces, etc.) plus the resolved --input under input/."
        ),
    )
    p.add_argument(
        "--golden-dir",
        type=Path,
        default=None,
        help="Destination directory for --save-golden (default: package golden_test_run/).",
    )
    args = p.parse_args(argv)

    if args.with_test_repair and not args.with_tester:
        print("error: --with-test-repair requires --with-tester", file=sys.stderr)
        return 2
    if args.with_template_repair and not args.with_template_generator and args.template_suite is None:
        print(
            "error: --with-template-repair requires --with-template-generator or --template-suite",
            file=sys.stderr,
        )
        return 2
    if args.with_external_tester and not args.external_source:
        print("error: --with-external-tester requires --external-source", file=sys.stderr)
        return 2

    from pivot_pipeline.run import run_pivot_pipeline

    nl_source = resolve_existing_user_file(args.input)

    summary = run_pivot_pipeline(
        repo_root=args.repo_root.resolve(),
        work_dir=args.work_dir,
        nl_source=nl_source,
        rules_json=args.rules_json,
        skip_phase0=args.skip_phase0,
        reset_progress=args.reset_progress,
        rules_per_chunk=args.rules_per_chunk,
        skip_critic=not args.with_critic,
        no_llm=args.no_llm,
        skip_registry=args.skip_registry,
        extract_only=args.extract_only,
        interactive_policy=args.interactive_policy,
        interactive_extract_abort=args.interactive_extract_abort,
        interactive_cross_coherence=args.interactive_cross_coherence,
        with_tester=args.with_tester,
        fail_on_tester_findings=args.fail_on_tester_findings,
        with_test_repair=args.with_test_repair,
        interactive_tester=args.interactive_tester,
        resume_tester_repair=args.resume_tester_repair,
        retriage_tester=args.retriage_tester,
        repairer_max_rounds=args.repairer_max_rounds,
        with_cross_critic=args.with_cross_critic,
        with_cross_repair=args.with_cross_repair,
        cross_coherence_skip_critic_gate=args.cross_coherence_skip_critic_gate,
        fail_on_precheck_warnings=args.fail_on_precheck_warnings,
        fail_on_varprod_trigger=args.fail_on_varprod_trigger,
        with_template_generator=args.with_template_generator,
        template_suite_path=args.template_suite,
        with_template_repair=args.with_template_repair,
        interactive_template_suite=args.interactive_template_suite,
        fail_on_template_findings=args.fail_on_template_findings,
        with_external_tester=args.with_external_tester,
        external_source=args.external_source,
        external_instance_id=args.external_instance_id,
        external_query_rule=args.external_query_rule,
        external_test_mode=args.external_test_mode,
        external_fill_orchestration=args.external_fill_orchestration,
        require_prior_critics=args.require_prior_critics,
        no_vnext_lowering=args.no_vnext_lowering,
        input_fn=input,
        print_fn=print,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.save_golden:
        from pivot_pipeline.golden_run import save_golden_snapshot

        dest = save_golden_snapshot(
            work_dir=args.work_dir.resolve(),
            nl_source=nl_source,
            golden_root=args.golden_dir.resolve() if args.golden_dir else None,
            summary=summary,
        )
        print(f"[pivot] golden snapshot written to {dest}", file=sys.stderr)
    outcome = summary.get("outcome", "")
    if outcome.startswith("blocked"):
        return (
            1
            if outcome
            not in (
                "blocked_critic",
                "blocked_semantic_repair_compile",
                "blocked_test_repair_compile",
                "blocked_template_repair_compile",
            )
            else 3
        )
    if summary.get("precheck_ok") is False:
        return 2
    if summary.get("varprod_trigger_ok") is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
