"""Interactive template suite diagnostic + repair + re-verify loop."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.assessment_linearize import build_and_write_assessment_artifacts
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh
from pivot_pipeline.repair_ir_validation import (
    RepairIrValidationError,
    compile_validation_hint,
    precompile_repaired_rules_validated,
)
from pivot_pipeline.rules_document import envelope_from_summary_or_body
from pivot_pipeline.template_diagnostician_agent import (
    TemplateDiagnosticOutputError,
    TemplateDiagnosticReport,
    finding_repair_eligible,
    format_template_diagnostic_terminal,
    run_template_diagnostician_with_repairs,
    template_repair_handoff_dict,
)
from pivot_pipeline.template_failure_bundle import (
    build_failure_bundles,
    load_template_run_report,
    report_needs_diagnostic,
)
from pivot_pipeline.template_repair_strategy import (
    repair_improved_subset,
    strategies_by_focus_rule,
    subset_issue_count,
    subset_worst_verdict_rank,
    validate_template_repair_transition,
)
from pivot_pipeline.template_repairer_agent import (
    MergeRepairerOutputError,
    append_template_repairer_trace,
    run_template_repairer,
    template_repair_compile_attempts_max,
    template_repair_max_rounds,
)
from pivot_pipeline.test_repair_registry import (
    is_repairer_api_error,
    run_test_repair_registry,
    test_repair_count_api_as_attempt,
    test_repair_registry_attempts_max,
)

BLOCKED_TEMPLATE_REPAIR_COMPILE = "blocked_template_repair_compile"
REPAIR_TOKEN = REPAIR_CRITIC_DRIFT_TOKEN


def template_report_ok(report: dict[str, Any]) -> bool:
    s = report.get("summary") or {}
    return int(s.get("failed", 0)) + int(s.get("inconclusive", 0)) == 0


def refresh_template_suite_if_rules_changed(
    *,
    work_dir: Path,
    policy_id: str,
    rules: list[dict[str, Any]],
    suite_path: Path,
    report_path: Path,
    summary: dict[str, Any],
    print_fn: Callable[..., None],
) -> dict[str, Any]:
    """
    Re-run the template suite when ``rules`` no longer match ``template_run_report.json``
    policy binding (e.g. after a manual ``rules_extracted.json`` edit).
    """
    from pivot_pipeline.template_suite.run import rules_json_sha256, run_template_suite

    current_sha = rules_json_sha256(rules)
    if report_path.is_file():
        trep = load_template_run_report(report_path)
        bound = (trep.get("policy_binding") or {}).get("rules_sha256")
        if bound == current_sha:
            return trep
    else:
        trep = {}

    prev = (trep.get("policy_binding") or {}).get("rules_sha256")
    print_fn(
        "[template_repair] Rules changed since last template suite run; "
        f"re-executing tests (report sha {str(prev)[:16]}… != current {current_sha[:16]}…).\n"
    )
    from pivot_pipeline.rules_document import write_rules_document_file

    rules_path = work_dir / "rules_extracted.json"
    write_rules_document_file(rules_path, policy_id=policy_id, rules=rules)
    trep = run_template_suite(
        suite_path=suite_path,
        rules_extracted_path=work_dir / "rules_extracted.json",
        out_report_path=report_path,
        write_report=True,
    )
    summary["template_suite_refreshed"] = True
    summary["template_run_report"] = str(report_path.resolve())
    summary["template_suite_summary"] = trep.get("summary")
    s = trep.get("summary") or {}
    print_fn(
        f"[template_repair] Template suite: passed={s.get('passed', 0)} "
        f"failed={s.get('failed', 0)} inconclusive={s.get('inconclusive', 0)}\n"
    )
    return trep


def _write_handoff(
    work_dir: Path,
    diag_report: TemplateDiagnosticReport,
    *,
    approved: set[str],
    ignored: set[str],
    processed_nl_path: Path,
    report_path: Path,
    suite_path: Path,
    bundles: list[dict[str, Any]],
    source_note: str,
    last_compile_validation_error: str | None = None,
    last_repair_error_stage: str | None = None,
    repair_session_count: int = 0,
) -> Path:
    path = work_dir / "template_repair_handoff.json"
    h = template_repair_handoff_dict(
        diag_report,
        approved_ids=sorted(approved),
        ignored_ids=sorted(ignored),
        processed_nl_path=processed_nl_path,
        template_run_report_path=report_path,
        suite_path=suite_path,
        failure_bundles=bundles,
        source_note=source_note,
        last_compile_validation_error=last_compile_validation_error,
        last_repair_error_stage=last_repair_error_stage,
        repair_session_count=repair_session_count,
    )
    path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _print_template_policy_gate(
    *,
    print_fn: Callable[..., None],
    n_approved: int,
    n_repair_ready: int,
    short: bool,
    compile_attempt_cap: int,
) -> None:
    if short:
        print_fn(
            f"\n[policy gate] Template Repairer compile budget exhausted ({compile_attempt_cap} "
            f"attempts in last REPAIR); policy artifacts unchanged.\n"
            f"  Same approved findings still active ({n_repair_ready} policy_ir of {n_approved} approved).\n"
            f"  Type {REPAIR_TOKEN!r} to run Template Repairer again, {PROCEED_INCOMPLETE_TOKEN!r} to waive, "
            "or Enter to abort.\n"
            "  Type 'retriage' to re-run finding triage (a/i).\n"
        )
    else:
        print_fn(
            "\n[policy gate] Template suite reported fail/inconclusive tests.\n"
            f"  Type {REPAIR_TOKEN!r} to run Template Repairer on approved policy_ir findings "
            f"(up to {compile_attempt_cap} compile tries per REPAIR), then re-verify.\n"
            f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue without template repair.\n"
            "  Type 'retriage' to re-run finding triage (a/i). Press Enter to abort.\n"
        )


def run_finding_triage(
    report: TemplateDiagnosticReport,
    *,
    input_fn: Callable[[str], str],
    print_fn: Callable[..., None],
) -> tuple[set[str], set[str]]:
    approved: set[str] = set()
    ignored: set[str] = set()
    findings = sorted(report.findings, key=lambda f: f.id)
    total = len(findings)
    if total == 0:
        return approved, ignored
    print_fn("\n=== Template finding triage ===\n")
    for idx, f in enumerate(findings, start=1):
        elig = " [repair-eligible]" if finding_repair_eligible(f) else ""
        print_fn(
            f"Finding {idx} of {total}: [{f.id}] {f.severity} / {f.category}{elig}\n"
            f"  Instances: {', '.join(f.instance_ids) or '(none)'}\n"
            f"  Rules: {', '.join(f.rule_ids) or '(none)'}\n"
            f"  {f.explanation}\n"
        )
        while True:
            ans = input_fn("  a = approve for repair   i = ignore   q = quit triage: ").strip().lower()
            if ans == "a":
                approved.add(f.id)
                break
            if ans == "i":
                ignored.add(f.id)
                break
            if ans == "q":
                return approved, ignored
            print_fn("  Invalid choice; use a, i, or q.\n")
    print_fn("")
    return approved, ignored


def _reverify_critic_enabled() -> bool:
    raw = os.getenv("PIVOT_TEMPLATE_REPAIR_REVERIFY_CRITIC", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def run_template_reverify_chain(
    *,
    work_dir: Path,
    nl_text_for_artifacts: str,
    nl_for_precheck: Path,
    nl_lines_reg: list[str],
    policy_id: str,
    rules: list[dict[str, Any]],
    meta_path: Path,
    skip_registry: bool,
    no_llm: bool,
    linearized: str | None,
    suite_path: Path,
    reverify_tester: bool,
    reverify_critic: bool,
    reverify_cross: bool,
    skip_critic: bool,
    with_cross_critic: bool,
    synth: str,
    print_fn: Callable[..., None],
    summary: dict[str, Any],
) -> tuple[str | None, dict[str, Any], str | None]:
    """Re-run tester → critic → cross (optional) → template suite. Returns (early, trep, linearized)."""
    from pivot_pipeline.post_model_workflow import run_pivot_tester_with_repairs

    linearized_out = linearized
    if linearized_out is None:
        linearized_out = build_and_write_assessment_artifacts(
            work_dir=work_dir, rules=rules, summary=summary
        )

    if reverify_tester and not no_llm:
        print_fn("\n[template_repair] Re-running Pivot Tester…")
        _raw, trep, _ = run_pivot_tester_with_repairs(
            processed_nl=nl_text_for_artifacts,
            linearized_model=linearized_out or "",
            work_dir=work_dir,
        )
        (work_dir / "tester_report.json").write_text(
            trep.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        summary["post_template_repair_tester_verdict"] = trep.verdict
        print_fn(f"[template_repair] Tester verdict: {trep.verdict}")
        if trep.verdict != "ok":
            print_fn(
                "[template_repair] Warning: Tester reported issues after template repair; "
                "review tester_report.json.\n"
            )

    if reverify_critic and _reverify_critic_enabled() and not skip_critic and not no_llm:
        from pivot_pipeline.critic_agent import run_pivot_critic_parsed

        print_fn("[template_repair] Re-running semantic critic…")
        synth_path = work_dir / "synthetic_en.md"
        synth_text = synth_path.read_text(encoding="utf-8") if synth_path.is_file() else synth
        _raw_c, critic_rep = run_pivot_critic_parsed(
            nl_text_for_artifacts,
            synth_text,
            varprod_rules_linearized=linearized_out or "",
        )
        (work_dir / "critic_report.json").write_text(
            critic_rep.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        summary["post_template_repair_critic_verdict"] = critic_rep.verdict
        print_fn(f"[template_repair] Critic verdict: {critic_rep.verdict}")
        if critic_rep.verdict == "DRIFT":
            print_fn(
                "[template_repair] Warning: semantic critic DRIFT after template repair; "
                "use semantic repair loop if needed.\n"
            )

    if (
        reverify_cross
        and _reverify_critic_enabled()
        and with_cross_critic
        and not no_llm
    ):
        from pivot_pipeline.cross_critic_agent import run_cross_critic_parsed_with_repairs

        print_fn("[template_repair] Re-running CrossCritic…")
        _raw_x, xc_rep, _ = run_cross_critic_parsed_with_repairs(
            nl_text_for_artifacts,
            linearized_out or "",
        )
        (work_dir / "cross_critic_report.json").write_text(
            xc_rep.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        summary["post_template_repair_cross_verdict"] = xc_rep.verdict
        print_fn(f"[template_repair] CrossCritic verdict: {xc_rep.verdict}")

    print_fn("[template_repair] Re-running template suite…")
    from pivot_pipeline.template_suite.run import run_template_suite

    trep = run_template_suite(
        suite_path=suite_path,
        rules_extracted_path=work_dir / "rules_extracted.json",
        out_report_path=work_dir / "template_run_report.json",
        write_report=True,
    )
    summary["template_suite_summary"] = trep["summary"]
    summary["template_run_report"] = str((work_dir / "template_run_report.json").resolve())
    print_fn(
        f"[template_repair] Template suite: passed={trep['summary']['passed']} "
        f"failed={trep['summary']['failed']} inconclusive={trep['summary']['inconclusive']}"
    )
    return None, trep, linearized_out


def run_template_interactive_loop(
    *,
    work_dir: Path,
    nl_text_for_artifacts: str,
    nl_for_precheck: Path,
    nl_lines_reg: list[str],
    policy_id: str,
    rules: list[dict[str, Any]],
    meta_path: Path,
    skip_registry: bool,
    no_llm: bool,
    skip_vnext_lowering: bool,
    interactive_any: bool,
    with_template_repair: bool,
    suite_path: Path,
    reverify_tester: bool,
    reverify_critic: bool,
    reverify_cross: bool,
    skip_critic: bool,
    with_cross_critic: bool,
    print_fn: Callable[..., None],
    input_fn: Callable[[str], str],
    summary: dict[str, Any],
    synth: str,
    meta: Any,
    z3_result: dict[str, Any],
    ok: bool,
    issues: list[Any],
    linearized: str | None,
) -> tuple[
    list[dict[str, Any]],
    Any,
    str,
    dict[str, Any],
    bool,
    list[Any],
    str | None,
    str | None,
]:
    report_path = work_dir / "template_run_report.json"
    if not report_path.is_file():
        print_fn("[template_repair] No template_run_report.json; skipping template repair loop.")
        return rules, meta, synth, z3_result, ok, issues, linearized, None

    trep = refresh_template_suite_if_rules_changed(
        work_dir=work_dir,
        policy_id=policy_id,
        rules=rules,
        suite_path=suite_path,
        report_path=report_path,
        summary=summary,
        print_fn=print_fn,
    )
    if summary.get("template_suite_refreshed") or linearized is None:
        linearized = build_and_write_assessment_artifacts(
            work_dir=work_dir, rules=rules, summary=summary
        )

    if not report_needs_diagnostic(trep):
        summary["template_repair_skipped"] = "all_tests_passed"
        return rules, meta, synth, z3_result, ok, issues, linearized, None

    if not with_template_repair:
        return rules, meta, synth, z3_result, ok, issues, linearized, None

    if no_llm:
        print_fn("[template_repair] --no-llm: cannot run diagnostician/repairer.")
        return rules, meta, synth, z3_result, ok, issues, linearized, None

    session_limit = template_repair_max_rounds()
    compile_cap = template_repair_compile_attempts_max()
    repair_sessions = 0
    summary["template_repair_rounds"] = 0

    processed_nl_path = nl_for_precheck
    suite_summary = dict(trep.get("summary") or {})
    bundles = build_failure_bundles(
        trep,
        suite_path=suite_path,
        linearized_model=linearized or "",
        processed_nl=nl_text_for_artifacts,
    )
    (work_dir / "template_failure_bundles.json").write_text(
        json.dumps(bundles, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    diag_report: TemplateDiagnosticReport | None = None
    needs_triage = False
    skip_triage_once = False
    sticky_approved: set[str] | None = None
    sticky_ignored: set[str] | None = None
    approved: set[str] = set()
    ignored: set[str] = set()
    repair_ready: list = []
    compile_attempt_cap = template_repair_compile_attempts_max()
    count_api = test_repair_count_api_as_attempt()

    while True:
        if diag_report is None:
            try:
                raw_d, diag_report, _ = run_template_diagnostician_with_repairs(
                    processed_nl=nl_text_for_artifacts,
                    linearized_model=linearized or "",
                    failure_bundles=bundles,
                    suite_summary=suite_summary,
                )
            except TemplateDiagnosticOutputError as e:
                summary["outcome"] = "blocked_template_diagnostic"
                summary["message"] = str(e)
                return rules, meta, synth, z3_result, ok, issues, linearized, "blocked_template_diagnostic"

            (work_dir / "template_diagnostic_report.json").write_text(
                diag_report.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            (work_dir / "template_diagnostic_result.txt").write_text(raw_d, encoding="utf-8")
            summary["template_diagnostic_verdict"] = diag_report.verdict
            print_fn(format_template_diagnostic_terminal(diag_report, suite_summary=suite_summary))
            needs_triage = True

        if not diag_report.findings:
            return rules, meta, synth, z3_result, ok, issues, linearized, None

        if not interactive_any:
            summary["template_repair_skipped"] = "non_interactive"
            print_fn(
                "[template_repair] Template issues present; pass --interactive-template-suite "
                "or --interactive-policy to triage and repair.\n"
            )
            return rules, meta, synth, z3_result, ok, issues, linearized, None

        user_waived = False
        while True:
            short_gate = False
            if skip_triage_once and sticky_approved is not None:
                approved = set(sticky_approved)
                ignored = set(sticky_ignored or ())
                skip_triage_once = False
                short_gate = True
            elif needs_triage:
                approved, ignored = run_finding_triage(
                    diag_report, input_fn=input_fn, print_fn=print_fn
                )
                sticky_approved = set(approved)
                sticky_ignored = set(ignored)
                needs_triage = False
            else:
                approved = set(sticky_approved or ())
                ignored = set(sticky_ignored or ())

            repair_ready = [
                f for f in diag_report.findings if f.id in approved and finding_repair_eligible(f)
            ]
            if not short_gate:
                print_fn(
                    f"Triage: approved={sorted(approved) or '(none)'} "
                    f"ignored={sorted(ignored) or '(none)'}\n"
                    f"  Policy-IR repair eligible among approved: "
                    f"{[f.id for f in repair_ready] or '(none)'}\n"
                )
                not_eligible = [
                    f for f in diag_report.findings if f.id in approved and not finding_repair_eligible(f)
                ]
                if not_eligible:
                    print_fn(
                        "  Approved but not repairable by Template Repairer (blame/repair_target):\n"
                        + "".join(
                            f"    - {f.id}: blame={f.blame}, repair_target={f.repair_target}\n"
                            for f in not_eligible
                        )
                    )

            _print_template_policy_gate(
                print_fn=print_fn,
                n_approved=len(approved),
                n_repair_ready=len(repair_ready),
                short=short_gate,
                compile_attempt_cap=compile_attempt_cap,
            )
            ans = input_fn(
                "[policy gate] Template issues — REPAIR / PROCEED_INCOMPLETE / Enter abort: "
            ).strip()
            ans_norm = ans.strip().upper()

            if not ans:
                raise PivotPipelineUserAbort("Template gate: empty input (abort)")

            if ans.lower() == "retriage":
                needs_triage = True
                sticky_approved = None
                sticky_ignored = None
                continue

            if ans_norm == PROCEED_INCOMPLETE_TOKEN:
                _write_handoff(
                    work_dir,
                    diag_report,
                    approved=approved,
                    ignored=ignored,
                    processed_nl_path=processed_nl_path,
                    report_path=report_path,
                    suite_path=suite_path,
                    bundles=bundles,
                    source_note="PROCEED_INCOMPLETE",
                    repair_session_count=repair_sessions,
                )
                summary["user_consented_template_issues"] = True
                user_waived = True
                break

            if ans_norm != REPAIR_TOKEN:
                print_fn(
                    f"[policy gate] Unrecognized input {ans!r}; use {REPAIR_TOKEN!r}, "
                    f"{PROCEED_INCOMPLETE_TOKEN!r}, 'retriage', or Enter to abort.\n"
                )
                continue

            if not repair_ready:
                print_fn(
                    "[policy gate] No approved policy_ir findings; Template Repairer only runs when "
                    "blame=policy_ir and repair_target=rules.\n"
                    f"  Type 'retriage', {PROCEED_INCOMPLETE_TOKEN!r}, or fix via cross-repair.\n"
                )
                continue

            if repair_sessions >= session_limit:
                summary["outcome"] = BLOCKED_TEMPLATE_REPAIR_COMPILE
                summary["message"] = (
                    f"template repair: exhausted {session_limit} REPAIR session(s) without compiling patch"
                )
                return (
                    rules,
                    meta,
                    synth,
                    z3_result,
                    ok,
                    issues,
                    linearized,
                    BLOCKED_TEMPLATE_REPAIR_COMPILE,
                )

            repair_sessions += 1
            summary["template_repair_rounds"] = repair_sessions
            initial_feedback = None
            if short_gate:
                handoff_file = work_dir / "template_repair_handoff.json"
                if handoff_file.is_file():
                    try:
                        initial_feedback = json.loads(handoff_file.read_text(encoding="utf-8")).get(
                            "last_compile_validation_error"
                        )
                    except (json.JSONDecodeError, OSError):
                        initial_feedback = None

            handoff_path = _write_handoff(
                work_dir,
                diag_report,
                approved=approved,
                ignored=ignored,
                processed_nl_path=processed_nl_path,
                report_path=report_path,
                suite_path=suite_path,
                bundles=bundles,
                source_note="Template Repairer",
                last_compile_validation_error=initial_feedback if isinstance(initial_feedback, str) else None,
                repair_session_count=repair_sessions,
            )
            summary["template_repair_handoff"] = str(handoff_path.resolve())
            h = json.loads(handoff_path.read_text(encoding="utf-8"))
            strat_by_rule = strategies_by_focus_rule(
                h.get("findings") or [],
                h.get("failure_bundles") or bundles,
            )
            target_instance_ids: set[str] = set()
            for f in h.get("findings") or []:
                if isinstance(f, dict):
                    for iid in f.get("instance_ids") or []:
                        target_instance_ids.add(str(iid))
            before_subset_report = load_template_run_report(report_path)
            rules_snapshot = copy.deepcopy(rules)

            compile_feedback: str | None = (
                initial_feedback if isinstance(initial_feedback, str) else None
            )
            merge_feedback: str | None = None
            repaired = False
            compile_attempt = 0
            last_error: BaseException | None = None
            last_stage: str | None = None
            api_retries_no_burn = 0

            while compile_attempt < compile_attempt_cap:
                if compile_attempt > 0:
                    print_fn(
                        f"[policy gate] Retrying Template Repairer (compile attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap})...\n"
                    )
                try:
                    out, json_retry = run_template_repairer(
                        policy_id=policy_id,
                        rules=rules,
                        handoff=h,
                        processed_nl_excerpt=nl_text_for_artifacts,
                        linearized_excerpt=linearized or "",
                        compile_validation_error=compile_feedback,
                        merge_validation_error=merge_feedback,
                    )
                except MergeRepairerOutputError as me:
                    print_fn(
                        f"[policy gate] Template Repairer returned incomplete rules "
                        f"(attempt {compile_attempt + 1}/{compile_attempt_cap}): {me}\n"
                    )
                    last_error = me
                    last_stage = "rules_merge"
                    merge_feedback = str(me)
                    compile_feedback = None
                    append_template_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_sessions,
                            "compile_attempt": compile_attempt + 1,
                            "error_stage": "rules_merge",
                            "error": str(me),
                        },
                    )
                    compile_attempt += 1
                    continue
                except Exception as re:
                    stage = "repairer_api" if is_repairer_api_error(re) else "repairer_json"
                    print_fn(
                        f"[policy gate] Template Repairer failed ({stage}, attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}): {re}\n"
                    )
                    last_error = re
                    last_stage = stage
                    append_template_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_sessions,
                            "compile_attempt": compile_attempt + 1,
                            "error_stage": stage,
                            "error": str(re),
                        },
                    )
                    if stage == "repairer_json":
                        compile_feedback = (
                            str(re)
                            + "\nchange_summary must be a list of objects "
                            '{ "finding_id", "rule_id", "change" }, not strings.'
                        )
                        merge_feedback = None
                        compile_attempt += 1
                        continue
                    if stage == "repairer_api" and not count_api:
                        api_retries_no_burn += 1
                        if api_retries_no_burn < 3:
                            continue
                    break

                append_template_repairer_trace(
                    work_dir,
                    {
                        "repair_session": repair_sessions,
                        "compile_attempt": compile_attempt + 1,
                        "change_summary": [c.model_dump() for c in out.change_summary],
                        "json_parse_retry_used": json_retry,
                    },
                )
                focus_ids = [
                    rid
                    for f in diag_report.findings
                    if f.id in approved
                    for rid in f.rule_ids
                ]
                try:
                    new_rules, dropped = precompile_repaired_rules_validated(
                        policy_id,
                        out.rules,
                        rules_before=rules,
                        focus_rule_ids=sorted(set(focus_ids)),
                        change_summary=[c.model_dump() for c in out.change_summary],
                    )
                    if dropped:
                        append_template_repairer_trace(
                            work_dir,
                            {"sanitize_dropped_keys": dropped},
                        )
                    validate_template_repair_transition(
                        rules_before=rules,
                        rules_after=new_rules,
                        focus_rule_ids=sorted(set(focus_ids)),
                        strategies_by_rule=strat_by_rule,
                    )
                except RepairIrValidationError as ve:
                    print_fn(
                        f"[policy gate] Template-repaired rules failed IR validation (attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}): {ve}\n"
                    )
                    last_error = ve
                    last_stage = "rules_compile"
                    compile_feedback = str(ve) + compile_validation_hint(ve)
                    merge_feedback = None
                    compile_attempt += 1
                    continue
                except Exception as ce:
                    print_fn(
                        f"[policy gate] Template-repaired rules failed compile (attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                    )
                    last_error = ce
                    last_stage = "rules_compile"
                    compile_feedback = str(ce) + compile_validation_hint(ce)
                    merge_feedback = None
                    compile_attempt += 1
                    continue

                if not skip_registry:
                    try:
                        _reg, new_rules, _reused = run_test_repair_registry(
                            work_dir=work_dir,
                            nl_lines_reg=nl_lines_reg,
                            rules_before=rules,
                            merged_rules=new_rules,
                            cli_skip_registry=False,
                            llm=pivot_llm_complete,
                        )
                    except Exception as re:
                        reg_stage = "registry_api" if is_repairer_api_error(re) else "registry_json"
                        print_fn(
                            f"[policy gate] Registry after template repair failed ({reg_stage}): {re}\n"
                        )
                        last_error = re
                        last_stage = reg_stage
                        compile_attempt += 1
                        continue

                rules_env = envelope_from_summary_or_body(summary, rules)
                try:
                    rules, meta, synth, z3_result, ok, issues, linearized = (
                        apply_repaired_rules_and_refresh(
                            work_dir=work_dir,
                            policy_id=policy_id,
                            rules=new_rules,
                            meta_path=meta_path,
                            nl_for_precheck=nl_for_precheck,
                            summary=summary,
                            after_rules_basename="rules_after_template_repair.json",
                            refresh_linearized=True,
                            rules_envelope=rules_env,
                            skip_vnext_lowering=skip_vnext_lowering,
                        )
                    )
                except Exception as ce:
                    print_fn(
                        f"[policy gate] Artifact refresh failed after template repair "
                        f"(attempt {compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                    )
                    last_error = ce
                    last_stage = "rules_compile"
                    compile_feedback = str(ce)
                    compile_attempt += 1
                    continue

                from pivot_pipeline.template_suite.run import run_template_suite

                probe_report = run_template_suite(
                    suite_path=suite_path,
                    rules_extracted_path=work_dir / "rules_extracted.json",
                    write_report=False,
                )
                if target_instance_ids and not repair_improved_subset(
                    before_report=before_subset_report,
                    after_report=probe_report,
                    instance_ids=target_instance_ids,
                ):
                    before_rank = subset_worst_verdict_rank(
                        before_subset_report, target_instance_ids
                    )
                    after_rank = subset_worst_verdict_rank(probe_report, target_instance_ids)
                    print_fn(
                        "[policy gate] Template repair did not improve approved instance(s) "
                        f"{sorted(target_instance_ids)} "
                        f"(verdict rank {before_rank}→{after_rank}, "
                        f"issues {subset_issue_count(before_subset_report, target_instance_ids)}"
                        f"→{subset_issue_count(probe_report, target_instance_ids)}); "
                        "rolling back patch.\n"
                    )
                    rules, meta, synth, z3_result, ok, issues, linearized = (
                        apply_repaired_rules_and_refresh(
                            work_dir=work_dir,
                            policy_id=policy_id,
                            rules=rules_snapshot,
                            meta_path=meta_path,
                            nl_for_precheck=nl_for_precheck,
                            summary=summary,
                            after_rules_basename="rules_after_template_repair.json",
                            refresh_linearized=True,
                            rules_envelope=rules_env,
                            skip_vnext_lowering=skip_vnext_lowering,
                        )
                    )
                    last_stage = "template_subset_regression"
                    compile_feedback = (
                        "Repair did not improve approved template instances (need pass, or at "
                        "least a better verdict: inconclusive→fail is OK if mutant becomes SAT). "
                        "Do not switch to LOGICAL_IMPLICATION with is_candidate/applicant_position "
                        "when counterfactual_flip had mutant UNSAT; do not leave K_OF_N without "
                        "result_variable when mutant stayed satisfied. Follow each finding "
                        "repair_strategy in handoff."
                    )
                    append_template_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_sessions,
                            "error_stage": "template_subset_regression",
                            "target_instance_ids": sorted(target_instance_ids),
                        },
                    )
                    compile_attempt += 1
                    continue

                print_fn(
                    f"[policy gate] Template-repaired rules compiled (attempt "
                    f"{compile_attempt + 1}/{compile_attempt_cap}); updating artifacts.\n"
                )
                repaired = True
                break

            if not repaired:
                compile_err = compile_feedback
                if last_stage in (None, "rules_compile", "rules_merge") and not compile_err and last_error:
                    compile_err = str(last_error)
                _write_handoff(
                    work_dir,
                    diag_report,
                    approved=approved,
                    ignored=ignored,
                    processed_nl_path=processed_nl_path,
                    report_path=report_path,
                    suite_path=suite_path,
                    bundles=bundles,
                    source_note="Template Repairer compile budget exhausted; awaiting REPAIR",
                    last_compile_validation_error=compile_err,
                    last_repair_error_stage=last_stage,
                    repair_session_count=repair_sessions,
                )
                skip_triage_once = True
                sticky_approved = set(approved)
                sticky_ignored = set(ignored)
                continue

            break

        if user_waived:
            return rules, meta, synth, z3_result, ok, issues, linearized, None

        _, trep_new, linearized = run_template_reverify_chain(
            work_dir=work_dir,
            nl_text_for_artifacts=nl_text_for_artifacts,
            nl_for_precheck=nl_for_precheck,
            nl_lines_reg=nl_lines_reg,
            policy_id=policy_id,
            rules=rules,
            meta_path=meta_path,
            skip_registry=skip_registry,
            no_llm=no_llm,
            linearized=linearized,
            suite_path=suite_path,
            reverify_tester=reverify_tester,
            reverify_critic=reverify_critic,
            reverify_cross=reverify_cross,
            skip_critic=skip_critic,
            with_cross_critic=with_cross_critic,
            synth=synth,
            print_fn=print_fn,
            summary=summary,
        )

        if template_report_ok(trep_new):
            summary["template_repair_passed"] = True
            return rules, meta, synth, z3_result, ok, issues, linearized, None

        trep = trep_new
        suite_summary = dict(trep.get("summary") or {})
        bundles = build_failure_bundles(
            trep,
            suite_path=suite_path,
            linearized_model=linearized or "",
            processed_nl=nl_text_for_artifacts,
        )
        diag_report = None
        needs_triage = True
        print_fn("\n[template_repair] Template suite still has issues; re-diagnosing…\n")


__all__ = [
    "BLOCKED_TEMPLATE_REPAIR_COMPILE",
    "run_template_interactive_loop",
    "template_report_ok",
]
